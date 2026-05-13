"""Entry point for `voxless` CLI."""

from __future__ import annotations

import logging
import signal
import sys

from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from .app import App
from .config import ensure_user_files, load_config
from .i18n import set_lang
from .logging_setup import setup_logging
from .overlay import RecorderOverlay
from .tray import Tray
from .ui_window import MainWindow

SINGLE_INSTANCE_KEY = "voxless-single-instance-v1"


_REOPEN_HANDLER = None  # keep a Python reference so it isn't GC'd
_REOPEN_SHOW_CALLBACK = None  # set by main() — fires when user clicks dock icon


def _deactivate_self() -> None:
    """Push voxless to the background. Called immediately after the
    overlay becomes visible during dictation so that AppKit's automatic
    "activate the app whose window just appeared" behaviour gets
    reversed before the user sees a dock bounce or focus shift."""
    try:
        from AppKit import NSApplication  # type: ignore
        NSApplication.sharedApplication().deactivate()
    except Exception:
        pass


def _install_reopen_router(log) -> None:
    """Route macOS' kAEReopenApplication AppleEvent to our show-window
    callback. kAEReopenApplication fires when the user clicks the dock
    icon while the app is running, double-clicks the app bundle while
    it's running, or activates it via Spotlight while running. These
    are all intentional "show me the window" actions and should open
    the main window.

    v0.3.3 installed a handler that SWALLOWED this event, which also
    killed legitimate dock-click activation — the user could not open
    the window at all without resorting to the tray menu. v0.3.9 routes
    the event into our authorized show path. Unsolicited shows are
    still filtered by MainWindow.event() / showEvent() guards."""
    global _REOPEN_HANDLER
    def _fcc(s: bytes) -> int:
        return (s[0] << 24) | (s[1] << 16) | (s[2] << 8) | s[3]

    try:
        from Foundation import NSAppleEventManager, NSObject  # type: ignore

        class _ReopenHandler(NSObject):
            def handleReopen_withReplyEvent_(self, event, reply):  # noqa: N802
                log.info("AppleEvent kAEReopenApplication — opening main window")
                cb = _REOPEN_SHOW_CALLBACK
                if cb is not None:
                    # Schedule on the Qt event loop so we don't touch
                    # QWidgets from the AppleEvent callback thread.
                    QTimer.singleShot(0, cb)
                return None

        handler = _ReopenHandler.alloc().init()
        manager = NSAppleEventManager.sharedAppleEventManager()
        manager.setEventHandler_andSelector_forEventClass_andEventID_(
            handler,
            'handleReopen:withReplyEvent:',
            _fcc(b'aevt'),
            _fcc(b'rapp'),
        )
        _REOPEN_HANDLER = handler
        log.info("Installed AppleEvent reopen router")
    except Exception:
        log.exception("Could not install reopen router")


def _try_send_show_to_existing() -> bool:
    """If another voxless instance is running, ping it to show the window
    and return True so we can exit. Otherwise return False."""
    sock = QLocalSocket()
    sock.connectToServer(SINGLE_INSTANCE_KEY)
    if sock.waitForConnected(300):
        sock.write(b"show\n")
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


def _start_single_instance_server(on_show) -> QLocalServer:
    QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)

    def _on_new_connection() -> None:
        client = server.nextPendingConnection()
        if client is None:
            return

        def _on_ready_read() -> None:
            try:
                _ = bytes(client.readAll())
            except Exception:
                pass
            on_show()
            client.disconnectFromServer()

        client.readyRead.connect(_on_ready_read)

    server.newConnection.connect(_on_new_connection)
    server.listen(SINGLE_INSTANCE_KEY)
    return server


def main() -> int:
    log = setup_logging()
    from .config import CONFIG_PATH
    is_first_run = not CONFIG_PATH.exists()
    try:
        ensure_user_files()
        cfg = load_config()
    except Exception as exc:
        log.exception("Failed to load configuration: %s", exc)
        return 1

    set_lang(cfg.ui_language)

    log.info(
        "Starting voxless 0.3.9 — hotkey=%s, whisper=%s, ollama=%s",
        cfg.hotkey,
        cfg.whisper.model,
        cfg.ollama.model if cfg.ollama.enabled else "disabled",
    )

    qt_app = QApplication.instance() or QApplication(sys.argv)
    QApplication.setStyle("Fusion")
    qt_app.setApplicationName("voxless")
    qt_app.setApplicationDisplayName("voxless")
    qt_app.setOrganizationName("voxless")
    qt_app.setQuitOnLastWindowClosed(False)

    if sys.platform == "darwin":
        # Route macOS' "reopen application" AppleEvent (kAEReopenApplication)
        # to our show-window callback. This event fires on dock-click,
        # Spotlight activation, and Finder double-click while voxless is
        # running. Without this, dock-click would do nothing.
        _install_reopen_router(log)

    if _try_send_show_to_existing():
        log.info("Another voxless instance is running — bringing it to front and exiting.")
        return 0

    backend = App(cfg)
    window = MainWindow(cfg)
    overlay = RecorderOverlay()

    user_opened_window: dict = {"flag": False}
    window._user_opened_flag = user_opened_window  # for closeEvent reset

    def _on_state(state: str) -> None:
        window.set_state(state)
        tray.set_state(state)

        # Mutual-exclusion rule: the floating overlay ("doc") and the main
        # configurations window must NEVER be visible at the same time.
        # During recording / processing the overlay is the active UI and
        # the main window has no business appearing.
        if state in ("recording", "processing"):
            if window.isVisible():
                log.info("hiding main window because state=%s (mutex with overlay)", state)
                user_opened_window["flag"] = False
                window._show_authorized = False  # re-arm the guard
                window.hide()
            if backend._cfg.show_overlay:
                overlay.set_state(state)
                # AppKit auto-activates apps with a dock icon whenever any
                # of their windows becomes visible. Immediately deactivate
                # so the dock doesn't bounce and the user's target app
                # stays frontmost. Done on a delay so the overlay has time
                # to actually appear before we kick focus back.
                if sys.platform == "darwin":
                    QTimer.singleShot(60, _deactivate_self)
            else:
                overlay.hide()
        else:
            # idle / error → overlay fades out, main window stays as the
            # user left it.
            if backend._cfg.show_overlay:
                overlay.set_state(state)
            else:
                overlay.hide()
            if state == "idle" and not user_opened_window["flag"]:
                if window.isVisible():
                    log.info("hiding main window after idle (was not user-opened)")
                    window.hide()

    def _on_transcribed(raw: str, clean: str) -> None:
        window.push_history(raw, clean)

    def _show_window() -> None:
        # Mutex: opening the main window hides the floating overlay so
        # both are never visible at once. If we're in the middle of
        # dictating (recording / processing) we must NOT honour the show
        # request — that would break the mutex from the other direction
        # and pop the config window during paste. The most common
        # trigger is the user launching a second voxless instance from
        # Spotlight / Finder while a dictation is in flight; that new
        # process sends a "show" message to us before exiting.
        if backend._state in ("recording", "processing"):
            log.info("ignoring show request — currently %s (mutex)", backend._state)
            return
        user_opened_window["flag"] = True
        overlay.hide()
        window.show_authorized()

    # Wire dock-click → _show_window via the AppleEvent router installed above.
    global _REOPEN_SHOW_CALLBACK
    _REOPEN_SHOW_CALLBACK = _show_window

    def _on_quit() -> None:
        log.info("Quit requested")
        backend.shutdown()
        QTimer.singleShot(150, qt_app.quit)

    backend.signals.state_changed.connect(_on_state)
    backend.signals.transcribed.connect(_on_transcribed)
    window.config_changed.connect(lambda _cfg: backend.reload_config())
    window.prompt_changed.connect(lambda _t: backend.reload_prompt())

    def _on_ai_action(text: str, action) -> None:
        import threading
        from PySide6.QtCore import QMetaObject, Q_ARG
        from PySide6.QtWidgets import QApplication

        def run() -> None:
            try:
                result = backend._llm.transform(text, action.system_prompt)
            except Exception:
                log.exception("AI action failed")
                window.show_toast(f"FALLÓ · {action.short}", variant="error")
                return
            QApplication.clipboard().setText(result)
            window.show_toast(f"{action.short} · COPIADO AL PORTAPAPELES")
            window.history_page.push(text, result)

        window.show_toast(f"PROCESANDO · {action.short}…", variant="info")
        threading.Thread(target=run, daemon=True).start()

    window.history_page.ai_action_requested.connect(_on_ai_action)

    tray = Tray(on_quit=_on_quit, on_show_window=_show_window)

    instance_server = _start_single_instance_server(_show_window)

    peak_timer = QTimer()
    peak_timer.setInterval(33)

    def _push_peak() -> None:
        try:
            peak = backend.recorder.peak_recent()
        except Exception:
            return
        window.push_audio_peak(peak)
        if backend._cfg.show_overlay:
            overlay.push_peak(peak)

    peak_timer.timeout.connect(_push_peak)
    peak_timer.start()

    signal.signal(signal.SIGINT, lambda *_: _on_quit())

    backend.start_background()

    # Only auto-show the window on first run. On subsequent launches voxless
    # lives only in the tray so it never steals focus from the app you're
    # dictating into.
    if is_first_run:
        _show_window()

    rc = qt_app.exec()
    instance_server.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
