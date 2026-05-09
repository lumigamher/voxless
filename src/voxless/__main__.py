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
        "Starting voxless 0.2.9 — hotkey=%s, whisper=%s, ollama=%s",
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
        if backend._cfg.show_overlay:
            overlay.set_state(state)
        else:
            overlay.hide()
        # Defensive: if voxless somehow gained focus during the recording
        # cycle and our main window snuck visible, hide it once we're idle
        # again — UNLESS the user opened it on purpose from the tray.
        if state == "idle" and not user_opened_window["flag"]:
            if window.isVisible():
                log.info("hiding main window after idle (was not user-opened)")
                window.hide()

    def _on_transcribed(raw: str, clean: str) -> None:
        window.push_history(raw, clean)

    def _show_window() -> None:
        user_opened_window["flag"] = True
        window.show_authorized()

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
