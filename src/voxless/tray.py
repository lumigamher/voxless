"""Cross-platform system tray backed by Qt's QSystemTrayIcon.

Qt owns the main thread and event loop; the tray lives inside it. This
works identically on macOS (NSStatusItem under the hood), Windows
(Shell_NotifyIcon), and Linux (StatusNotifier/legacy).
"""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .config import CONFIG_PATH, PROMPT_PATH
from .logging_setup import LOG_PATH

log = logging.getLogger(__name__)

ICON_SIZE = 32

STATE_COLORS = {
    "idle": "#3c3c3c",
    "recording": "#dc3232",
    "processing": "#f0aa1e",
    "error": "#b40000",
}

STATUS_LABELS = {
    "idle": "Listo",
    "recording": "Grabando…",
    "processing": "Procesando…",
    "error": "Error (revisa logs)",
}


def _open_path(path: Path) -> None:
    p = str(path)
    if sys.platform == "darwin":
        subprocess.Popen(["open", p])
    elif sys.platform.startswith("win"):
        subprocess.Popen(["explorer", p], shell=False)
    else:
        subprocess.Popen(["xdg-open", p])


def _make_pixmap(state: str, size: int = ICON_SIZE) -> QPixmap:
    color = QColor(STATE_COLORS.get(state, STATE_COLORS["idle"]))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    pad = max(2, size // 8)
    body_w = size - pad * 2 - size // 4
    body_h = size - pad * 2 - size // 4
    body_x = (size - body_w) // 2
    body_y = pad
    p.drawRoundedRect(body_x, body_y, body_w, body_h, body_w // 3, body_w // 3)
    stem_w = max(2, size // 16)
    p.drawRect(size // 2 - stem_w // 2, body_y + body_h, stem_w, size // 8)
    base_w = body_w
    p.drawRoundedRect(
        (size - base_w) // 2,
        body_y + body_h + size // 8,
        base_w,
        max(2, size // 16),
        2,
        2,
    )
    p.end()
    return pm


def _make_icon(state: str) -> QIcon:
    icon = QIcon()
    for s in (16, 22, 32, 48, 64):
        icon.addPixmap(_make_pixmap(state, s))
    return icon


class Tray:
    def __init__(
        self,
        on_quit: Callable[[], None] | None = None,
        on_show_window: Callable[[], None] | None = None,
    ) -> None:
        self._on_quit = on_quit
        self._on_show_window = on_show_window
        self._state = "idle"

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(_make_icon("idle"))
        self._tray.setToolTip("voxless — Listo")

        menu = QMenu()
        self._status_action = QAction(STATUS_LABELS["idle"], menu)
        self._status_action.setEnabled(False)
        menu.addAction(self._status_action)
        menu.addSeparator()

        show_action = QAction("Abrir voxless", menu)
        show_action.triggered.connect(self._handle_show)
        menu.addAction(show_action)
        menu.addSeparator()

        cfg_action = QAction("Editar config", menu)
        cfg_action.triggered.connect(lambda: _open_path(CONFIG_PATH))
        menu.addAction(cfg_action)

        prompt_action = QAction("Editar prompt", menu)
        prompt_action.triggered.connect(lambda: _open_path(PROMPT_PATH))
        menu.addAction(prompt_action)

        logs_action = QAction("Abrir logs", menu)
        logs_action.triggered.connect(lambda: _open_path(LOG_PATH))
        menu.addAction(logs_action)
        menu.addSeparator()

        quit_action = QAction("Salir", menu)
        quit_action.triggered.connect(self._handle_quit)
        menu.addAction(quit_action)

        self._menu = menu
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._handle_show()

    def set_state(self, state: str) -> None:
        self._state = state
        self._tray.setIcon(_make_icon(state))
        self._tray.setToolTip(f"voxless — {STATUS_LABELS.get(state, state)}")
        self._status_action.setText(STATUS_LABELS.get(state, state))

    def _handle_show(self) -> None:
        if self._on_show_window:
            try:
                self._on_show_window()
            except Exception:
                log.exception("on_show_window handler failed")

    def _handle_quit(self) -> None:
        if self._on_quit:
            try:
                self._on_quit()
            except Exception:
                log.exception("on_quit handler failed")
