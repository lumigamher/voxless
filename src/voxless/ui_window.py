"""Main application window — sidebar + pages, live waveform, history.

v0.1.4 redesign: cleaner Linear/Raycast-inspired chrome, real SVG icons,
row-based settings layout, hero home screen, toast on save.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from datetime import datetime

import numpy as np
from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QFontDatabase, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .config import Config, save_config, save_prompt
from .icons import render_icon
from .permissions import Permission, list_permissions
from .prompts import load_prompt
from .toast import Toast

log = logging.getLogger(__name__)

ACCENT = "#dc2626"
ACCENT_HOVER = "#b91c1c"
ACCENT_TINT = "rgba(220, 38, 38, 0.10)"

QSS = """
* {
  font-family: -apple-system, "SF Pro Text", "SF Pro Display", "Segoe UI Variable",
               "Segoe UI", system-ui, sans-serif;
  color: #0a0a0a;
}

QMainWindow, #Root { background: #fafafa; }

#Sidebar {
  background: #f4f4f5;
  border-right: 1px solid #e5e5e5;
}
#SidebarBrand { padding: 22px 18px 18px 18px; }
#SidebarBrandText { font-size: 17px; font-weight: 700; color: #0a0a0a; letter-spacing: -0.01em; }
#SidebarBrandDot {
  background: """ + ACCENT + """;
  border-radius: 6px;
  min-width: 12px; min-height: 12px;
  max-width: 12px; max-height: 12px;
}
#SidebarSection {
  color: #6b7280;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 18px 22px 6px 22px;
  text-transform: uppercase;
}

QListWidget#NavList {
  background: transparent;
  border: none;
  outline: 0;
  font-size: 13px;
}
QListWidget#NavList::item {
  padding: 7px 14px;
  border-radius: 7px;
  margin: 1px 10px;
  color: #1f2937;
}
QListWidget#NavList::item:selected {
  background: rgba(255, 255, 255, 0.95);
  color: #0a0a0a;
  font-weight: 600;
}
QListWidget#NavList::item:hover:!selected {
  background: rgba(255, 255, 255, 0.55);
}

#VersionFooter {
  color: #9ca3af;
  font-size: 10px;
  padding: 12px 22px;
  letter-spacing: 0.04em;
}

#PageHeader {
  padding: 28px 36px 20px 36px;
  background: transparent;
  border-bottom: 1px solid #ececec;
}
QLabel#PageTitle {
  font-size: 24px;
  font-weight: 700;
  color: #0a0a0a;
  letter-spacing: -0.02em;
}
QLabel#PageSub {
  font-size: 13px;
  color: #6b7280;
  margin-top: 2px;
}

#PageBody { background: transparent; }

QFrame#Row { border-bottom: 1px solid #ececec; }
QFrame#Row:last { border-bottom: none; }
QLabel#RowTitle { font-size: 13.5px; font-weight: 600; color: #111; }
QLabel#RowDesc  { font-size: 12px; color: #6b7280; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 7px 10px;
  selection-background-color: """ + ACCENT + """;
  font-size: 13px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus { border-color: """ + ACCENT + """; }
QComboBox::drop-down { border: 0; width: 20px; }

QPushButton {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 7px 14px;
  color: #0a0a0a;
  font-size: 13px;
  font-weight: 500;
}
QPushButton:hover { background: #f3f4f6; }
QPushButton:pressed { background: #e5e7eb; }
QPushButton:disabled { color: #9ca3af; background: #f9fafb; }

QPushButton#Primary {
  background: """ + ACCENT + """;
  color: white;
  border: 1px solid """ + ACCENT_HOVER + """;
  font-weight: 600;
}
QPushButton#Primary:hover { background: """ + ACCENT_HOVER + """; }
QPushButton#Ghost {
  background: transparent;
  border: 1px solid transparent;
  color: """ + ACCENT + """;
  font-weight: 600;
}
QPushButton#Ghost:hover { background: """ + ACCENT_TINT + """; }

QListWidget#History {
  background: transparent;
  border: 1px solid #ececec;
  border-radius: 12px;
  outline: 0;
  padding: 4px;
}
QListWidget#History::item {
  background: transparent;
  border-bottom: 1px solid #f3f4f6;
  border-radius: 0;
  margin: 0;
  padding: 12px 14px;
  color: #111;
}
QListWidget#History::item:hover { background: #f9fafb; }
QListWidget#History::item:selected {
  background: """ + ACCENT_TINT + """;
  color: #111;
}

QCheckBox { color: #111; font-size: 13px; }
QCheckBox::indicator {
  width: 18px; height: 18px;
  border: 1px solid #d1d5db; border-radius: 5px; background: white;
}
QCheckBox::indicator:checked {
  background: """ + ACCENT + """;
  border-color: """ + ACCENT_HOVER + """;
  image: none;
}

#Hero {
  background: white;
  border: 1px solid #ececec;
  border-radius: 18px;
  padding: 36px;
}
#HeroPill {
  background: rgba(220, 38, 38, 0.10);
  color: """ + ACCENT + """;
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
#HeroHotkey {
  background: rgba(15, 23, 42, 0.04);
  color: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  padding: 14px 22px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
#HeroHint  { color: #6b7280; font-size: 13px; }
#HeroLast  { color: #6b7280; font-size: 11px; font-weight: 600;
             letter-spacing: 0.08em; text-transform: uppercase; }
#HeroLastText { color: #111; font-size: 14px; }
"""

QSS_DARK = """
* { color: #f5f5f7; }
QMainWindow, #Root { background: #0c0c0d; }
#Sidebar { background: #141416; border-right-color: #1f1f23; }
#SidebarBrandText { color: #fafafa; }
#SidebarSection { color: #9ca3af; }
QListWidget#NavList::item { color: #d4d4d8; }
QListWidget#NavList::item:selected {
  background: rgba(255,255,255,0.06); color: #fafafa;
}
QListWidget#NavList::item:hover:!selected { background: rgba(255,255,255,0.03); }
#PageHeader { border-bottom-color: #1f1f23; }
QLabel#PageTitle { color: #fafafa; }
QLabel#PageSub  { color: #9ca3af; }
QFrame#Row { border-bottom-color: #1f1f23; }
QLabel#RowTitle { color: #f5f5f7; }
QLabel#RowDesc { color: #9ca3af; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
  background: #18181b; border-color: #27272a; color: #f5f5f7;
}
QPushButton {
  background: #18181b; color: #f5f5f7; border-color: #27272a;
}
QPushButton:hover { background: #27272a; }
QPushButton:pressed { background: #3f3f46; }
QListWidget#History { border-color: #1f1f23; }
QListWidget#History::item { color: #f5f5f7; border-bottom-color: #1f1f23; }
QListWidget#History::item:hover { background: #18181b; }
QCheckBox { color: #f5f5f7; }
QCheckBox::indicator { background: #18181b; border-color: #3f3f46; }
#Hero { background: #18181b; border-color: #27272a; }
#HeroHotkey { background: rgba(255,255,255,0.04); color: #fafafa; border-color: rgba(255,255,255,0.08); }
#HeroLastText { color: #f5f5f7; }
#VersionFooter { color: #6b7280; }
"""

NAV_ITEMS = [
    ("home",        "Inicio",     "home"),
    ("general",     "General",    "settings"),
    ("permissions", "Permisos",   "shield"),
    ("whisper",     "Whisper",    "mic"),
    ("ollama",      "Ollama",     "spark"),
    ("prompt",      "Prompt",     "text"),
    ("history",     "Historial",  "clock"),
]

STATE_TEXT = {
    "idle":       ("Listo",      "Mantén la tecla configurada para grabar"),
    "recording":  ("Grabando",   "Habla — al soltar la tecla se transcribe"),
    "processing": ("Procesando", "Whisper + Ollama trabajando"),
    "error":      ("Error",      "Revisa los logs para detalles"),
}

STATE_DOT_COLOR = {
    "idle": "#10b981",
    "recording": ACCENT,
    "processing": "#f59e0b",
    "error": ACCENT,
}


def _is_dark_mode() -> bool:
    if sys.platform == "darwin":
        try:
            import subprocess
            r = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=1,
            )
            return r.returncode == 0 and "Dark" in r.stdout
        except Exception:
            return False
    return False


_MAC_VK_TO_NAME = {
    61: "right_option", 58: "left_option",
    54: "cmd_r", 55: "cmd_l",
    62: "ctrl_r", 59: "ctrl_l",
    60: "shift_r", 56: "shift_l",
    63: "fn",
}

_WIN_VK_TO_NAME = {
    0xA5: "right_option", 0xA4: "left_option",
    0xA3: "ctrl_r", 0xA2: "ctrl_l",
    0xA1: "shift_r", 0xA0: "shift_l",
    0x5C: "cmd_r", 0x5B: "cmd_l",
}


def _named_key_from_event(event: QKeyEvent) -> str | None:
    key = event.key()
    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F35:
        return f"f{key - Qt.Key.Key_F1 + 1}"
    if key == Qt.Key.Key_Space:
        return "space"
    if key == Qt.Key.Key_Tab:
        return "tab"
    if key == Qt.Key.Key_Escape:
        return "esc"
    if key == Qt.Key.Key_CapsLock:
        return "caps_lock"
    if key in (Qt.Key.Key_Alt, Qt.Key.Key_Control, Qt.Key.Key_Meta, Qt.Key.Key_Shift):
        nv = event.nativeVirtualKey()
        if sys.platform == "darwin":
            mapped = _MAC_VK_TO_NAME.get(nv)
            if mapped:
                return mapped
        elif sys.platform.startswith("win"):
            mapped = _WIN_VK_TO_NAME.get(nv)
            if mapped:
                return mapped
        if key == Qt.Key.Key_Alt:
            return "alt"
        if key == Qt.Key.Key_Control:
            return "ctrl"
        if key == Qt.Key.Key_Meta:
            return "cmd" if sys.platform == "darwin" else "ctrl"
        if key == Qt.Key.Key_Shift:
            return "shift"
    if event.text() and len(event.text()) == 1 and event.text().strip():
        ch = event.text().lower()
        if ch.isalnum():
            return ch
    return None


def _spec_pretty(spec: str) -> str:
    if not spec:
        return "—"
    parts = [p.strip("<> ") for p in spec.split("+")]
    label_map = {
        "right_option": "⌥ Right", "left_option": "⌥ Left", "alt": "⌥",
        "cmd": "⌘", "cmd_l": "⌘ Left", "cmd_r": "⌘ Right",
        "ctrl": "⌃", "ctrl_l": "⌃ Left", "ctrl_r": "⌃ Right",
        "shift": "⇧", "shift_l": "⇧ Left", "shift_r": "⇧ Right",
        "space": "Space", "tab": "Tab", "esc": "Esc",
        "caps_lock": "Caps Lock", "fn": "Fn",
    }
    out = []
    for p in parts:
        if p in label_map:
            out.append(label_map[p])
        elif p.startswith("f") and p[1:].isdigit():
            out.append(p.upper())
        else:
            out.append(p.upper())
    return " + ".join(out)


class HotkeyRecorder(QPushButton):
    captured = Signal(str)

    def __init__(self, current: str = "") -> None:
        super().__init__()
        self._spec = current
        self._recording = False
        self.setMinimumHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._toggle)
        self._update()

    def spec(self) -> str:
        return self._spec

    def set_spec(self, spec: str) -> None:
        self._spec = spec
        self._recording = False
        self._update()

    def _toggle(self) -> None:
        self._recording = not self._recording
        if self._recording:
            self.setFocus(Qt.FocusReason.OtherFocusReason)
            self.grabKeyboard()
        else:
            self.releaseKeyboard()
        self._update()

    def _update(self) -> None:
        if self._recording:
            self.setText("Presiona una tecla…   (Esc para cancelar)")
            self.setStyleSheet(
                "QPushButton { background:" + ACCENT_TINT + "; border:1px solid " + ACCENT
                + "; border-radius:8px; padding:8px 14px; font-weight:600; color:" + ACCENT + "; }"
            )
        else:
            self.setText(_spec_pretty(self._spec))
            self.setStyleSheet("")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._recording:
            return super().keyPressEvent(event)
        mods = event.modifiers()
        if event.key() == Qt.Key.Key_Escape and not mods:
            self._recording = False
            self.releaseKeyboard()
            self._update()
            return
        name = _named_key_from_event(event)
        if not name:
            return
        ms: list[str] = []
        if mods & Qt.KeyboardModifier.ControlModifier and name not in ("ctrl", "ctrl_l", "ctrl_r"):
            ms.append("ctrl")
        if mods & Qt.KeyboardModifier.AltModifier and name not in ("alt", "left_option", "right_option"):
            ms.append("alt")
        if mods & Qt.KeyboardModifier.MetaModifier and name not in ("cmd", "cmd_l", "cmd_r"):
            ms.append("cmd")
        if mods & Qt.KeyboardModifier.ShiftModifier and name not in ("shift", "shift_l", "shift_r"):
            ms.append("shift")
        spec = "+".join(f"<{x}>" for x in ms) + "+" + name if ms else name
        self._spec = spec
        self._recording = False
        self.releaseKeyboard()
        self._update()
        self.captured.emit(spec)


class StatusDot(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(12, 12)
        self._color = QColor(STATE_DOT_COLOR["idle"])
        self._pulse = 0.0
        self._direction = 1.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def set_state(self, state: str) -> None:
        self._color = QColor(STATE_DOT_COLOR.get(state, STATE_DOT_COLOR["idle"]))
        if state in ("recording", "processing"):
            self._timer.start(33)
        else:
            self._timer.stop()
            self._pulse = 0.0
        self.update()

    def _tick(self) -> None:
        self._pulse += 0.07 * self._direction
        if self._pulse >= 1.0:
            self._pulse = 1.0
            self._direction = -1.0
        elif self._pulse <= 0.0:
            self._pulse = 0.0
            self._direction = 1.0
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._timer.isActive():
            halo = QColor(self._color)
            halo.setAlphaF(0.30 * self._pulse)
            p.setBrush(halo)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(self.rect())
        p.setBrush(self._color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.rect().adjusted(2, 2, -2, -2))


class WaveformView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._levels: list[float] = [0.0] * 64
        self._active = False

    def push(self, peak: float) -> None:
        self._levels.append(min(1.0, peak * 6.0))
        if len(self._levels) > 64:
            self._levels = self._levels[-64:]
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._levels = [0.0] * 64
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        bar_w = max(3, w // len(self._levels) - 3)
        gap = 3
        total = len(self._levels) * (bar_w + gap)
        x = (w - total) // 2
        cy = h / 2
        color = QColor(ACCENT) if self._active else QColor("#cfcfd2")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        for level in self._levels:
            bar_h = max(4, int(level * (h - 12)))
            p.drawRoundedRect(x, int(cy - bar_h / 2), bar_w, bar_h, 2, 2)
            x += bar_w + gap


def _page_header(title: str, subtitle: str) -> QWidget:
    w = QFrame()
    w.setObjectName("PageHeader")
    layout = QVBoxLayout(w)
    layout.setContentsMargins(36, 28, 36, 20)
    layout.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    s = QLabel(subtitle)
    s.setObjectName("PageSub")
    layout.addWidget(t)
    layout.addWidget(s)
    return w


def _row(title: str, description: str | None, control: QWidget,
         extra_controls: list[QWidget] | None = None) -> QFrame:
    """Linear-style settings row: title + description on the left,
    control(s) flush-right, separated by a hairline divider."""
    row = QFrame()
    row.setObjectName("Row")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(36, 14, 36, 14)
    layout.setSpacing(20)

    text_col = QVBoxLayout()
    text_col.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("RowTitle")
    text_col.addWidget(t)
    if description:
        d = QLabel(description)
        d.setObjectName("RowDesc")
        d.setWordWrap(True)
        text_col.addWidget(d)
    layout.addLayout(text_col, 1)

    control.setMinimumWidth(180)
    control.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    layout.addWidget(control)
    if extra_controls:
        for c in extra_controls:
            layout.addWidget(c)
    return row


def _save_bar(on_save: Callable[[], None]) -> QWidget:
    bar = QFrame()
    bar.setStyleSheet("background: transparent;")
    h = QHBoxLayout(bar)
    h.setContentsMargins(36, 16, 36, 28)
    h.addStretch(1)
    btn = QPushButton("Guardar cambios")
    btn.setObjectName("Primary")
    btn.clicked.connect(on_save)
    h.addWidget(btn)
    return bar


def _scrollable(content: QWidget) -> QWidget:
    from PySide6.QtWidgets import QScrollArea
    sa = QScrollArea()
    sa.setWidget(content)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setStyleSheet("QScrollArea { background: transparent; }")
    return sa


class HomePage(QWidget):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self._cfg = cfg
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(36, 28, 36, 36)
        wrap.setSpacing(20)

        hero = QFrame()
        hero.setObjectName("Hero")
        h = QVBoxLayout(hero)
        h.setSpacing(18)
        h.setContentsMargins(36, 36, 36, 36)

        pill_row = QHBoxLayout()
        pill_row.setSpacing(10)
        self.dot = StatusDot()
        pill_row.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.status_pill = QLabel("Listo")
        self.status_pill.setObjectName("HeroPill")
        pill_row.addWidget(self.status_pill, 0, Qt.AlignmentFlag.AlignVCenter)
        pill_row.addStretch(1)
        h.addLayout(pill_row)

        title = QLabel("Mantén la tecla y habla")
        title.setStyleSheet("font-size:28px; font-weight:700; letter-spacing:-0.02em; color:#0a0a0a;")
        h.addWidget(title)

        sub = QLabel("voxless transcribe localmente con Whisper y limpia el texto con Ollama. Privado, rápido, offline.")
        sub.setObjectName("HeroHint")
        sub.setWordWrap(True)
        h.addWidget(sub)

        hk_row = QHBoxLayout()
        self.hotkey_label = QLabel(_spec_pretty(cfg.hotkey))
        self.hotkey_label.setObjectName("HeroHotkey")
        hk_row.addWidget(self.hotkey_label)
        hk_row.addStretch(1)
        h.addLayout(hk_row)

        self.waveform = WaveformView()
        self.waveform.setMinimumHeight(56)
        h.addWidget(self.waveform)

        wrap.addWidget(hero)

        last_box = QFrame()
        last_box.setStyleSheet(
            "background: white; border:1px solid #ececec; border-radius: 14px; padding: 0;"
        )
        lb = QVBoxLayout(last_box)
        lb.setContentsMargins(24, 18, 24, 22)
        lb.setSpacing(8)
        lt = QLabel("Última transcripción")
        lt.setObjectName("HeroLast")
        lb.addWidget(lt)
        self.last_text = QLabel("Aún no hay transcripciones — graba una para empezar.")
        self.last_text.setObjectName("HeroLastText")
        self.last_text.setWordWrap(True)
        lb.addWidget(self.last_text)
        wrap.addWidget(last_box)

        wrap.addStretch(1)

    def set_state(self, state: str) -> None:
        text, _sub = STATE_TEXT.get(state, STATE_TEXT["idle"])
        self.status_pill.setText(text)
        self.dot.set_state(state)
        self.waveform.set_active(state == "recording")

    def set_hotkey(self, spec: str) -> None:
        self.hotkey_label.setText(_spec_pretty(spec))


class GeneralPage(QWidget):
    def __init__(self, cfg: Config, on_save: Callable[[Config], None]) -> None:
        super().__init__()
        self._cfg = cfg
        self._on_save = on_save

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_page_header("General", "Hotkey, modo de activación y comportamiento de grabación."))

        body = QFrame()
        body.setObjectName("PageBody")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.hotkey_recorder = HotkeyRecorder(cfg.hotkey)
        bl.addWidget(_row(
            "Hotkey",
            "Click en el botón y presiona la tecla (o combinación) que quieras usar.",
            self.hotkey_recorder,
        ))

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Mantener presionado (push-to-talk)", "hold")
        self.mode_combo.addItem("Tap: tocar para iniciar / tocar para terminar", "toggle")
        idx = self.mode_combo.findData(cfg.hotkey_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        bl.addWidget(_row(
            "Modo de activación",
            "Cómo se controla la grabación con la tecla.",
            self.mode_combo,
        ))

        self.min_ms = QSpinBox()
        self.min_ms.setRange(0, 5000)
        self.min_ms.setSingleStep(50)
        self.min_ms.setSuffix(" ms")
        self.min_ms.setValue(cfg.min_record_ms)
        bl.addWidget(_row(
            "Duración mínima",
            "Grabaciones más cortas se ignoran. Útil para evitar pulsaciones accidentales.",
            self.min_ms,
        ))

        self.sound = QCheckBox("")
        self.sound.setChecked(cfg.sound_feedback)
        bl.addWidget(_row(
            "Sonido al grabar",
            "Reproducir un click sutil al iniciar y detener.",
            self.sound,
        ))

        outer.addWidget(_scrollable(body), 1)
        outer.addWidget(_save_bar(self._save))

    def _save(self) -> None:
        self._cfg.hotkey = self.hotkey_recorder.spec().strip() or "right_option"
        self._cfg.hotkey_mode = self.mode_combo.currentData()
        self._cfg.min_record_ms = int(self.min_ms.value())
        self._cfg.sound_feedback = self.sound.isChecked()
        self._on_save(self._cfg)


class WhisperPage(QWidget):
    def __init__(self, cfg: Config, on_save: Callable[[Config], None]) -> None:
        super().__init__()
        self._cfg = cfg
        self._on_save = on_save

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_page_header("Whisper", "Modelo local de transcripción (faster-whisper)."))

        body = QFrame()
        body.setObjectName("PageBody")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText(cfg.whisper.model)
        bl.addWidget(_row(
            "Modelo",
            "Más grande = más exacto, pero más lento. small es buen punto medio.",
            self.model_combo,
        ))

        self.lang_edit = QLineEdit(cfg.whisper.language or "")
        self.lang_edit.setPlaceholderText("auto (vacío) o ej. es, en, fr")
        bl.addWidget(_row("Idioma", "Vacío para auto-detectar.", self.lang_edit))

        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["int8", "int8_float16", "float16", "float32"])
        self.compute_combo.setCurrentText(cfg.whisper.compute_type)
        bl.addWidget(_row("Precisión",
                          "int8 funciona bien y es rápido. float16/32 piden GPU.",
                          self.compute_combo))

        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cpu"])
        self.device_combo.setCurrentText(cfg.whisper.device)
        bl.addWidget(_row("Device", "auto detecta GPU si está disponible.", self.device_combo))

        outer.addWidget(_scrollable(body), 1)
        outer.addWidget(_save_bar(self._save))

    def _save(self) -> None:
        self._cfg.whisper.model = self.model_combo.currentText()
        lang = self.lang_edit.text().strip() or None
        self._cfg.whisper.language = lang
        self._cfg.whisper.compute_type = self.compute_combo.currentText()
        self._cfg.whisper.device = self.device_combo.currentText()
        self._on_save(self._cfg)


class OllamaPage(QWidget):
    def __init__(self, cfg: Config, on_save: Callable[[Config], None]) -> None:
        super().__init__()
        self._cfg = cfg
        self._on_save = on_save

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_page_header("Ollama", "Modelo local de limpieza de texto."))

        body = QFrame()
        body.setObjectName("PageBody")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.enabled = QCheckBox("")
        self.enabled.setChecked(cfg.ollama.enabled)
        bl.addWidget(_row(
            "Limpieza con Ollama",
            "Si lo desactivas, voxless pega el texto crudo de Whisper.",
            self.enabled,
        ))

        self.url = QLineEdit(cfg.ollama.url)
        bl.addWidget(_row("URL",
                          "URL del servidor Ollama. Local por defecto.",
                          self.url))

        self.model = QLineEdit(cfg.ollama.model)
        self.model.setPlaceholderText("ej. gemma3:1b, llama3.2:3b, qwen2.5:3b")
        bl.addWidget(_row("Modelo",
                          "Cualquier modelo que tengas con `ollama pull`.",
                          self.model))

        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(1.0, 600.0)
        self.timeout.setDecimals(1)
        self.timeout.setSuffix(" s")
        self.timeout.setValue(cfg.ollama.timeout_s)
        bl.addWidget(_row("Timeout",
                          "Si Ollama tarda más, voxless pega el texto sin limpiar.",
                          self.timeout))

        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setDecimals(2)
        self.temperature.setValue(cfg.ollama.temperature)
        bl.addWidget(_row("Temperatura",
                          "0 = muy literal, 1 = más libre.",
                          self.temperature))

        outer.addWidget(_scrollable(body), 1)
        outer.addWidget(_save_bar(self._save))

    def _save(self) -> None:
        self._cfg.ollama.enabled = self.enabled.isChecked()
        self._cfg.ollama.url = self.url.text().strip()
        self._cfg.ollama.model = self.model.text().strip()
        self._cfg.ollama.timeout_s = float(self.timeout.value())
        self._cfg.ollama.temperature = float(self.temperature.value())
        self._on_save(self._cfg)


class PromptPage(QWidget):
    def __init__(self, on_save: Callable[[str], None]) -> None:
        super().__init__()
        self._on_save = on_save

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_page_header(
            "Prompt", "Plantilla que recibe Ollama. Reglas de estilo + few-shot."))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(36, 16, 36, 0)
        bl.setSpacing(8)

        self.editor = QPlainTextEdit()
        self.editor.setPlainText(load_prompt())
        font = QFont("Menlo")
        if not font.exactMatch():
            font = QFont("Consolas")
        font.setPointSize(11)
        self.editor.setFont(font)
        self.editor.setMinimumHeight(360)
        bl.addWidget(self.editor, 1)

        outer.addWidget(body, 1)

        bar = QFrame()
        h = QHBoxLayout(bar)
        h.setContentsMargins(36, 16, 36, 28)
        h.addStretch(1)
        btn = QPushButton("Guardar prompt")
        btn.setObjectName("Primary")
        btn.clicked.connect(lambda: self._on_save(self.editor.toPlainText()))
        h.addWidget(btn)
        outer.addWidget(bar)


class HistoryPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_page_header(
            "Historial",
            "Últimas transcripciones de esta sesión (máx. 100). Click para copiar."))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(36, 16, 36, 16)
        bl.setSpacing(12)

        self.list = QListWidget()
        self.list.setObjectName("History")
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list.itemDoubleClicked.connect(self._copy_selected)
        bl.addWidget(self.list, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        copy_btn = QPushButton("Copiar")
        copy_btn.clicked.connect(self._copy_selected)
        clear_btn = QPushButton("Limpiar")
        clear_btn.setObjectName("Ghost")
        clear_btn.clicked.connect(self.list.clear)
        actions.addWidget(copy_btn)
        actions.addWidget(clear_btn)
        bl.addLayout(actions)

        outer.addWidget(body, 1)

    def push(self, raw: str, clean: str) -> None:
        if self.list.count() >= 100:
            self.list.takeItem(self.list.count() - 1)
        ts = datetime.now().strftime("%H:%M:%S")
        text = clean if clean else raw
        if clean and clean.strip() != raw.strip():
            display = f"{ts}  ·  {text}\n              raw: {raw}"
        else:
            display = f"{ts}  ·  {text}"
        item = QListWidgetItem(display)
        item.setData(Qt.ItemDataRole.UserRole, text)
        self.list.insertItem(0, item)

    def _copy_selected(self, *_args) -> None:
        from PySide6.QtWidgets import QApplication
        item = self.list.currentItem()
        if not item:
            return
        text = item.data(Qt.ItemDataRole.UserRole) or item.text()
        QApplication.clipboard().setText(text)


class PermissionsPage(QWidget):
    request_made = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[tuple[Permission, QLabel]] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_page_header(
            "Permisos",
            "Necesarios para que voxless escuche tu hotkey y grabe el micrófono globalmente."))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        perms = list_permissions()
        if not perms:
            note = QLabel("Tu plataforma no requiere configuración adicional.")
            note.setStyleSheet("color:#6b7280; padding:24px 36px;")
            bl.addWidget(note)
        else:
            for perm in perms:
                bl.addWidget(self._build_row(perm))

        tip = QLabel(
            "<b>Tip</b> — si el panel de System Settings no deja seleccionar voxless, "
            "arrastra <code>/Applications/voxless.app</code> desde Finder al panel. "
            "Tras conceder un permiso, vuelve y pulsa <i>Verificar</i>."
        )
        tip.setWordWrap(True)
        tip.setTextFormat(Qt.TextFormat.RichText)
        tip.setStyleSheet(
            "color:#374151; background:#f9fafb; border:1px solid #ececec;"
            " border-radius:10px; padding:12px 14px; margin: 16px 36px;"
            " font-size:12px;"
        )
        bl.addWidget(tip)

        outer.addWidget(_scrollable(body), 1)

        bar = QFrame()
        h = QHBoxLayout(bar)
        h.setContentsMargins(36, 12, 36, 28)
        h.addStretch(1)
        refresh = QPushButton("Verificar de nuevo")
        refresh.clicked.connect(self.refresh)
        h.addWidget(refresh)
        outer.addWidget(bar)

    def _build_row(self, perm: Permission) -> QWidget:
        status = QLabel("…")
        status.setMinimumWidth(96)
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        controls: list[QWidget] = [status]
        if perm.request is not None:
            req_btn = QPushButton(perm.request_label)
            req_btn.setObjectName("Primary")
            req_btn.clicked.connect(self._make_request_handler(perm))
            controls.append(req_btn)
        open_btn = QPushButton("Abrir ajustes")
        open_btn.clicked.connect(perm.open_settings)
        controls.append(open_btn)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        spacer.setFixedSize(0, 0)

        row = _row(perm.title, perm.description, spacer, extra_controls=controls)
        self._rows.append((perm, status))
        self._render(perm, status)
        return row

    def _make_request_handler(self, perm: Permission):
        def handler() -> None:
            try:
                if perm.request:
                    perm.request()
            except Exception:
                log.exception("request handler failed")
            self.request_made.emit()
            QTimer.singleShot(800, self.refresh)
        return handler

    def _render(self, perm: Permission, label: QLabel) -> None:
        try:
            st = perm.detect()
        except Exception:
            st = "unknown"
        if st == "granted":
            label.setText("Concedido")
            label.setStyleSheet(
                "color:#0a7c0a; background:rgba(16,185,129,0.14);"
                " border-radius:8px; padding:5px 12px; font-weight:600; font-size:12px;"
            )
        elif st == "denied":
            label.setText("Falta")
            label.setStyleSheet(
                "color:#b40000; background:rgba(220,38,38,0.12);"
                " border-radius:8px; padding:5px 12px; font-weight:600; font-size:12px;"
            )
        else:
            label.setText("—")
            label.setStyleSheet(
                "color:#6b7280; background:rgba(107,114,128,0.10);"
                " border-radius:8px; padding:5px 12px; font-weight:600; font-size:12px;"
            )

    def refresh(self) -> None:
        for perm, lbl in self._rows:
            self._render(perm, lbl)


class MainWindow(QMainWindow):
    config_changed = Signal(object)
    prompt_changed = Signal(str)
    quit_requested = Signal()

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.setWindowTitle("voxless")
        self.setMinimumSize(QSize(900, 620))
        self.resize(QSize(960, 660))
        self._cfg = cfg

        root = QWidget()
        root.setObjectName("Root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(216)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 12)
        side_layout.setSpacing(0)

        brand = QFrame()
        brand.setObjectName("SidebarBrand")
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(22, 22, 22, 14)
        bl.setSpacing(10)
        dot = QLabel()
        dot.setObjectName("SidebarBrandDot")
        bl.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
        name = QLabel("voxless")
        name.setObjectName("SidebarBrandText")
        bl.addWidget(name, 1, Qt.AlignmentFlag.AlignVCenter)
        side_layout.addWidget(brand)

        section = QLabel("Workspace")
        section.setObjectName("SidebarSection")
        side_layout.addWidget(section)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        self.nav.setIconSize(QSize(16, 16))
        self.nav.setSpacing(0)
        for _key, label, icon_name in NAV_ITEMS:
            item = QListWidgetItem(label)
            item.setIcon(render_icon(icon_name, 16, "#374151"))
            item.setSizeHint(QSize(0, 32))
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)
        side_layout.addWidget(self.nav, 1)

        version_lbl = QLabel("voxless · 0.1.4")
        version_lbl.setObjectName("VersionFooter")
        side_layout.addWidget(version_lbl)

        root_layout.addWidget(sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.home_page = HomePage(cfg)
        self.general_page = GeneralPage(cfg, self._handle_config_save)
        self.permissions_page = PermissionsPage()
        self.whisper_page = WhisperPage(cfg, self._handle_config_save)
        self.ollama_page = OllamaPage(cfg, self._handle_config_save)
        self.prompt_page = PromptPage(self._handle_prompt_save)
        self.history_page = HistoryPage()
        for w in (
            self.home_page, self.general_page, self.permissions_page,
            self.whisper_page, self.ollama_page, self.prompt_page,
            self.history_page,
        ):
            self.stack.addWidget(w)
        self.nav.currentRowChanged.connect(self._on_nav_change)
        content_layout.addWidget(self.stack, 1)

        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)

        self._apply_qss()

    def _on_nav_change(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        if self.stack.currentWidget() is self.permissions_page:
            self.permissions_page.refresh()

    def _apply_qss(self) -> None:
        qss = QSS
        if _is_dark_mode():
            qss = QSS + QSS_DARK
        self.setStyleSheet(qss)

    def _handle_config_save(self, cfg: Config) -> None:
        try:
            save_config(cfg)
        except Exception as exc:
            log.exception("Failed to save config")
            self.show_toast(f"No se pudo guardar: {exc}", variant="error")
            return
        self.home_page.set_hotkey(cfg.hotkey)
        self.config_changed.emit(cfg)
        self.show_toast("Configuración guardada")

    def _handle_prompt_save(self, text: str) -> None:
        try:
            save_prompt(text)
        except Exception as exc:
            log.exception("Failed to save prompt")
            self.show_toast(f"No se pudo guardar el prompt: {exc}", variant="error")
            return
        self.prompt_changed.emit(text)
        self.show_toast("Prompt guardado")

    def show_toast(self, text: str, variant: str = "success") -> None:
        toast = Toast(text, variant=variant, parent=self)  # type: ignore[arg-type]
        toast.show_for(self)

    def set_state(self, state: str) -> None:
        self.home_page.set_state(state)

    def push_audio_peak(self, peak: float) -> None:
        self.home_page.waveform.push(peak)

    def push_history(self, raw: str, clean: str) -> None:
        self.history_page.push(raw, clean)
        self.home_page.last_text.setText(clean if clean else raw)

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
