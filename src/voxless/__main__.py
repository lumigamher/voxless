"""Entry point for `voxless` CLI."""

from __future__ import annotations

import logging
import signal
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .app import App
from .config import ensure_user_files, load_config
from .logging_setup import setup_logging
from .tray import Tray
from .ui_window import MainWindow


def main() -> int:
    log = setup_logging()
    try:
        ensure_user_files()
        cfg = load_config()
    except Exception as exc:
        log.exception("Failed to load configuration: %s", exc)
        return 1

    log.info(
        "Starting voxless 0.1.0 — hotkey=%s, whisper=%s, ollama=%s",
        cfg.hotkey,
        cfg.whisper.model,
        cfg.ollama.model if cfg.ollama.enabled else "disabled",
    )

    qt_app = QApplication.instance() or QApplication(sys.argv)
    qt_app.setApplicationName("voxless")
    qt_app.setApplicationDisplayName("voxless")
    qt_app.setOrganizationName("voxless")
    qt_app.setQuitOnLastWindowClosed(False)

    backend = App(cfg)
    window = MainWindow(cfg)

    def _on_state(state: str) -> None:
        window.set_state(state)
        tray.set_state(state)

    def _on_transcribed(raw: str, clean: str) -> None:
        window.push_history(raw, clean)

    def _show_window() -> None:
        window.show()
        window.raise_()
        window.activateWindow()

    def _on_quit() -> None:
        log.info("Quit requested")
        backend.shutdown()
        QTimer.singleShot(150, qt_app.quit)

    backend.signals.state_changed.connect(_on_state)
    backend.signals.transcribed.connect(_on_transcribed)
    window.config_changed.connect(lambda _cfg: backend.reload_config())
    window.prompt_changed.connect(lambda _t: backend.reload_prompt())

    tray = Tray(on_quit=_on_quit, on_show_window=_show_window)

    peak_timer = QTimer()
    peak_timer.setInterval(33)

    def _push_peak() -> None:
        try:
            peak = backend.recorder.peak_recent()
        except Exception:
            return
        window.push_audio_peak(peak)

    peak_timer.timeout.connect(_push_peak)
    peak_timer.start()

    signal.signal(signal.SIGINT, lambda *_: _on_quit())

    backend.start_background()
    _show_window()
    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())
