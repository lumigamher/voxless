"""voxless main window — Studio Print Shop aesthetic.

Editorial × analog studio gear: cream paper × ink × VU-meter amber. Numbered TOC nav,
italic serif display, monospace technical readouts, hairline rules, em-dashes.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime

import numpy as np
from PySide6.QtCore import (
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
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .config import Config, save_config, save_prompt
from .permissions import Permission, list_permissions
from .prompts import load_prompt
from .toast import Toast

log = logging.getLogger(__name__)

# ── design tokens ─────────────────────────────────────────────────────────
PAPER       = "#f4f0e6"   # warm cream page bg
PAPER_HI    = "#fbf8ef"   # slightly warmer card surface
INK         = "#1a1614"   # warm near-black
INK_SOFT    = "#3d3733"
INK_MUTE    = "#7a716a"
RULE        = "#d8cfbd"   # hairline color (paper)
ACCENT      = "#c2410c"   # warm amber, VU-meter peak
ACCENT_HOT  = "#9a3412"
ACCENT_TINT = "rgba(194, 65, 12, 0.10)"
PEAK        = "#dc2626"   # full red, danger only

DARK_PAPER  = "#13110f"
DARK_HI     = "#1c1815"
DARK_INK    = "#f4f0e6"
DARK_MUTE   = "#8a807a"
DARK_RULE   = "#33302c"

# resolved at runtime
def _serif() -> str:
    return '"Iowan Old Style", "Charter", "Georgia", "Cambria", serif'

def _mono() -> str:
    return '"SF Mono", "Menlo", "JetBrains Mono", "Cascadia Mono", "Consolas", monospace'

def _sans() -> str:
    return '-apple-system, "SF Pro Text", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif'


def _is_dark_mode() -> bool:
    if sys.platform == "darwin":
        try:
            r = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=1,
            )
            return r.returncode == 0 and "Dark" in r.stdout
        except Exception:
            return False
    return False


def QSS_LIGHT() -> str:
    return f"""
* {{ font-family: {_sans()}; color: {INK}; }}

QMainWindow, #Root {{ background: {PAPER}; }}

/* ── sidebar ───────────────────────────────────────────────────────── */
#Sidebar {{
  background: {PAPER};
  border-right: 1px solid {RULE};
}}
#SidebarBrand {{
  font-family: {_serif()};
  font-style: italic;
  font-size: 18px;
  font-weight: 500;
  color: {INK};
  padding: 28px 24px 4px 24px;
  letter-spacing: -0.01em;
}}
#SidebarTagline {{
  font-family: {_mono()};
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.18em;
  color: {INK_MUTE};
  padding: 0 24px 22px 24px;
  text-transform: uppercase;
}}
#SidebarSection {{
  font-family: {_mono()};
  color: {INK_MUTE};
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.20em;
  padding: 12px 24px 8px 24px;
  text-transform: uppercase;
}}
QListWidget#NavList {{
  background: transparent;
  border: none;
  outline: 0;
}}
QListWidget#NavList::item {{
  padding: 7px 14px 7px 24px;
  margin: 0;
  color: {INK_SOFT};
  border-left: 2px solid transparent;
  font-family: {_mono()};
  font-size: 12px;
  letter-spacing: 0.02em;
}}
QListWidget#NavList::item:selected {{
  color: {INK};
  border-left-color: {ACCENT};
  background: rgba(255,255,255,0.55);
  font-weight: 600;
}}
QListWidget#NavList::item:hover:!selected {{
  color: {INK};
  background: rgba(0,0,0,0.025);
}}
#VersionFooter {{
  font-family: {_mono()};
  color: {INK_MUTE};
  font-size: 9px;
  letter-spacing: 0.14em;
  padding: 14px 24px 18px 24px;
  text-transform: uppercase;
}}

/* ── page header ───────────────────────────────────────────────────── */
#PageHeader {{ background: transparent; border-bottom: 1px solid {RULE}; }}
QLabel#PageEyebrow {{
  font-family: {_mono()};
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.22em;
  color: {INK_MUTE};
  text-transform: uppercase;
}}
QLabel#PageTitle {{
  font-family: {_serif()};
  font-size: 32px;
  font-style: italic;
  font-weight: 500;
  color: {INK};
  letter-spacing: -0.015em;
}}
QLabel#PageSub {{
  font-family: {_serif()};
  font-size: 14px;
  font-style: italic;
  color: {INK_MUTE};
}}

/* ── settings rows ─────────────────────────────────────────────────── */
QFrame#Row {{ border-bottom: 1px solid {RULE}; background: transparent; }}
QLabel#RowIndex {{
  font-family: {_mono()};
  font-size: 11px;
  color: {INK_MUTE};
  letter-spacing: 0.10em;
  font-weight: 600;
}}
QLabel#RowTitle {{
  font-family: {_serif()};
  font-size: 16px;
  color: {INK};
}}
QLabel#RowDesc {{
  font-family: {_mono()};
  font-size: 11px;
  color: {INK_MUTE};
  letter-spacing: 0.01em;
}}

/* ── inputs ────────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
  background: {PAPER_HI};
  border: 1px solid {RULE};
  border-radius: 4px;
  padding: 8px 12px;
  selection-background-color: {ACCENT};
  selection-color: white;
  font-family: {_mono()};
  font-size: 12px;
  color: {INK};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QPlainTextEdit:hover {{ border-color: {INK_SOFT}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus {{
  border-color: {ACCENT};
  background: white;
}}
QComboBox::drop-down {{ border: 0; width: 22px; }}
QComboBox::down-arrow {{
  width: 8px; height: 8px;
}}

/* ── buttons ───────────────────────────────────────────────────────── */
QPushButton {{
  background: {PAPER_HI};
  border: 1px solid {RULE};
  border-radius: 4px;
  padding: 9px 16px;
  color: {INK};
  font-family: {_mono()};
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
}}
QPushButton:hover {{
  background: white;
  border-color: {INK_SOFT};
}}
QPushButton:pressed {{ background: {RULE}; }}
QPushButton:disabled {{
  color: {INK_MUTE};
  background: {PAPER_HI};
  border-color: {RULE};
}}

QPushButton#Primary {{
  background: {INK};
  color: {PAPER};
  border: 1px solid {INK};
}}
QPushButton#Primary:hover {{
  background: {ACCENT};
  border-color: {ACCENT_HOT};
}}
QPushButton#Primary:pressed {{ background: {ACCENT_HOT}; }}

QPushButton#Accent {{
  background: {ACCENT};
  color: white;
  border: 1px solid {ACCENT_HOT};
}}
QPushButton#Accent:hover {{ background: {ACCENT_HOT}; }}

QPushButton#Ghost {{
  background: transparent;
  border: 1px solid transparent;
  color: {ACCENT};
}}
QPushButton#Ghost:hover {{ background: {ACCENT_TINT}; }}

/* ── checkboxes ────────────────────────────────────────────────────── */
QCheckBox {{ color: {INK}; font-family: {_mono()}; font-size: 11px; spacing: 10px; }}
QCheckBox::indicator {{
  width: 16px; height: 16px;
  border: 1px solid {INK_MUTE}; border-radius: 3px;
  background: {PAPER_HI};
}}
QCheckBox::indicator:hover {{ border-color: {INK}; }}
QCheckBox::indicator:checked {{
  background: {INK};
  border-color: {INK};
  image: none;
}}

/* ── history list ──────────────────────────────────────────────────── */
QListWidget#History {{
  background: {PAPER_HI};
  border: 1px solid {RULE};
  border-radius: 8px;
  outline: 0;
  padding: 0;
}}
QListWidget#History::item {{
  background: transparent;
  border-bottom: 1px solid {RULE};
  border-radius: 0;
  padding: 14px 18px;
  color: {INK};
  font-family: {_serif()};
  font-size: 13px;
}}
QListWidget#History::item:hover {{ background: rgba(0,0,0,0.02); }}
QListWidget#History::item:selected {{
  background: {ACCENT_TINT};
  color: {INK};
}}

/* ── scrollbar ─────────────────────────────────────────────────────── */
QScrollBar:vertical {{
  background: transparent; width: 10px; margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
  background: rgba(26,22,20,0.18); border-radius: 4px; min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: rgba(26,22,20,0.32); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

/* ── hero ──────────────────────────────────────────────────────────── */
#HeroFrame {{ background: transparent; }}
QLabel#HeroEyebrow {{
  font-family: {_mono()};
  font-size: 11px;
  letter-spacing: 0.22em;
  font-weight: 600;
  color: {INK_MUTE};
  text-transform: uppercase;
}}
QLabel#HeroTitle {{
  font-family: {_serif()};
  font-size: 56px;
  font-style: italic;
  font-weight: 500;
  color: {INK};
  letter-spacing: -0.025em;
  line-height: 1;
}}
QLabel#HeroLead {{
  font-family: {_serif()};
  font-size: 17px;
  font-style: italic;
  color: {INK_SOFT};
  line-height: 26px;
}}
#HeroHotkeyBox {{
  background: {INK};
  border: 1px solid {INK};
  border-radius: 8px;
}}
QLabel#HeroHotkeyLabel {{
  font-family: {_mono()};
  font-size: 9px;
  color: rgba(244,240,230,0.55);
  letter-spacing: 0.22em;
  text-transform: uppercase;
}}
QLabel#HeroHotkeyValue {{
  font-family: {_serif()};
  font-style: italic;
  font-size: 28px;
  color: {PAPER};
  letter-spacing: -0.01em;
}}
QLabel#HeroMetric {{
  font-family: {_mono()};
  font-size: 9px;
  color: {INK_MUTE};
  letter-spacing: 0.18em;
  text-transform: uppercase;
}}

#LastBox {{
  background: {PAPER_HI};
  border: 1px solid {RULE};
  border-radius: 8px;
}}
QLabel#LastEyebrow {{
  font-family: {_mono()};
  font-size: 10px;
  color: {INK_MUTE};
  letter-spacing: 0.20em;
  font-weight: 600;
  text-transform: uppercase;
}}
QLabel#LastText {{
  font-family: {_serif()};
  font-style: italic;
  font-size: 16px;
  color: {INK};
  line-height: 24px;
}}

/* ── tip / status ──────────────────────────────────────────────────── */
#TipBox {{
  background: {PAPER_HI};
  border: 1px solid {RULE};
  border-radius: 6px;
  font-family: {_mono()};
  font-size: 11px;
  color: {INK_SOFT};
}}
"""


def QSS_DARK() -> str:
    return QSS_LIGHT().replace(PAPER, DARK_PAPER).replace(PAPER_HI, DARK_HI) \
        .replace(INK_SOFT, DARK_INK).replace(INK_MUTE, DARK_MUTE) \
        .replace(RULE, DARK_RULE).replace(INK, DARK_INK)


# ─── data ───────────────────────────────────────────────────────────────────

NAV_ITEMS = [
    ("home",        "INICIO"),
    ("general",     "GENERAL"),
    ("permissions", "PERMISOS"),
    ("whisper",     "WHISPER"),
    ("ollama",      "OLLAMA"),
    ("prompt",      "PROMPT"),
    ("history",     "HISTORIAL"),
]

STATE_TEXT = {
    "idle":       "READY",
    "recording":  "REC",
    "processing": "PROCESSING",
    "error":      "ERROR",
}

STATE_DOT_COLOR = {
    "idle": "#10b981",
    "recording": ACCENT,
    "processing": "#d97706",
    "error": PEAK,
}


# ── hotkey ─────────────────────────────────────────────────────────────────
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
        "right_option": "⌥R", "left_option": "⌥L", "alt": "⌥",
        "cmd": "⌘", "cmd_l": "⌘L", "cmd_r": "⌘R",
        "ctrl": "⌃", "ctrl_l": "⌃L", "ctrl_r": "⌃R",
        "shift": "⇧", "shift_l": "⇧L", "shift_r": "⇧R",
        "space": "Space", "tab": "Tab", "esc": "Esc",
        "caps_lock": "Caps", "fn": "Fn",
    }
    out = []
    for p in parts:
        if p in label_map:
            out.append(label_map[p])
        elif p.startswith("f") and p[1:].isdigit():
            out.append(p.upper())
        else:
            out.append(p.upper())
    return " · ".join(out)


class HotkeyRecorder(QPushButton):
    captured = Signal(str)

    def __init__(self, current: str = "") -> None:
        super().__init__()
        self._spec = current
        self._recording = False
        self.setMinimumHeight(40)
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
            self.setText("PRESIONA UNA TECLA · ESC PARA CANCELAR")
            self.setStyleSheet(
                f"QPushButton {{ background:{ACCENT_TINT}; border:1px solid {ACCENT}; "
                f"color:{ACCENT}; border-radius:4px; padding:9px 16px; "
                f"font-family:{_mono()}; font-size:10px; font-weight:700; "
                f"letter-spacing:0.14em; }}"
            )
        else:
            self.setText(_spec_pretty(self._spec).upper())
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


# ─── decorations ────────────────────────────────────────────────────────────

class StatusDot(QWidget):
    def __init__(self, size: int = 10) -> None:
        super().__init__()
        self.setFixedSize(size, size)
        self._size = size
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
            self._direction = -1.0
            self._pulse = 1.0
        elif self._pulse <= 0.0:
            self._direction = 1.0
            self._pulse = 0.0
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._timer.isActive():
            halo = QColor(self._color)
            halo.setAlphaF(0.25 * self._pulse)
            p.setBrush(halo)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(self.rect())
        p.setBrush(self._color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.rect().adjusted(2, 2, -2, -2))


class VuMeter(QWidget):
    """VU-style waveform with dB tick marks. Bars warm-amber, peaks shift red."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._levels: list[float] = [0.0] * 56
        self._active = False

    def push(self, peak: float) -> None:
        self._levels.append(min(1.0, peak * 6.5))
        if len(self._levels) > 56:
            self._levels = self._levels[-56:]
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._levels = [0.0] * 56
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        # tick marks at -30, -20, -10, -3 dB (informational, not data-true)
        rule_color = QColor(INK_MUTE)
        rule_color.setAlphaF(0.35)
        p.setPen(QPen(rule_color, 1, Qt.PenStyle.SolidLine))
        font = QFont("Menlo", 7)
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 110)
        p.setFont(font)
        for frac, label in ((0.65, "-30"), (0.40, "-20"), (0.18, "-10"), (0.04, "-3")):
            y = int(h / 2 + frac * (h / 2))
            p.drawLine(8, y, w - 30, y)
            p.drawText(w - 26, y + 3, f"{label}dB")

        # bars
        n = len(self._levels)
        bar_w = max(2, (w - 80) // n - 2)
        gap = 2
        total = n * (bar_w + gap)
        x = (w - 80 - total) // 2 + 8
        cy = h / 2
        for level in self._levels:
            bar_h = max(3, int(level * (h - 14)))
            color = QColor(ACCENT) if self._active else QColor("#bcb1a0")
            if level > 0.85:
                color = QColor(PEAK)
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, int(cy - bar_h / 2), bar_w, bar_h, 1, 1)
            x += bar_w + gap


# ─── building blocks ────────────────────────────────────────────────────────

def _scrollable(content: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidget(content)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    sa.viewport().setStyleSheet("background: transparent;")
    return sa


def _page_header(eyebrow: str, title: str, subtitle: str) -> QWidget:
    w = QFrame()
    w.setObjectName("PageHeader")
    layout = QVBoxLayout(w)
    layout.setContentsMargins(48, 36, 48, 22)
    layout.setSpacing(8)
    e = QLabel(eyebrow)
    e.setObjectName("PageEyebrow")
    layout.addWidget(e)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    layout.addWidget(t)
    s = QLabel(subtitle)
    s.setObjectName("PageSub")
    s.setWordWrap(True)
    layout.addWidget(s)
    return w


def _row(index: str, title: str, description: str | None, control: QWidget,
         extra_controls: list[QWidget] | None = None) -> QFrame:
    row = QFrame()
    row.setObjectName("Row")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(48, 18, 48, 18)
    layout.setSpacing(20)

    idx = QLabel(index)
    idx.setObjectName("RowIndex")
    idx.setFixedWidth(36)
    idx.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    layout.addWidget(idx, 0)

    text_col = QVBoxLayout()
    text_col.setSpacing(3)
    t = QLabel(title)
    t.setObjectName("RowTitle")
    text_col.addWidget(t)
    if description:
        d = QLabel(description)
        d.setObjectName("RowDesc")
        d.setWordWrap(True)
        text_col.addWidget(d)
    layout.addLayout(text_col, 1)

    control.setMinimumWidth(220)
    layout.addWidget(control)
    if extra_controls:
        for c in extra_controls:
            layout.addWidget(c)
    return row


def _save_bar(on_save: Callable[[], None]) -> QWidget:
    bar = QFrame()
    bar.setStyleSheet(f"background: transparent; border-top: 1px solid {RULE};")
    h = QHBoxLayout(bar)
    h.setContentsMargins(48, 18, 48, 24)
    h.addStretch(1)
    btn = QPushButton("GUARDAR CAMBIOS")
    btn.setObjectName("Primary")
    btn.clicked.connect(on_save)
    h.addWidget(btn)
    return bar


# ─── pages ─────────────────────────────────────────────────────────────────

class HomePage(QWidget):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self._cfg = cfg
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(48, 40, 48, 40)
        wrap.setSpacing(28)

        # eyebrow with status dot
        eye_row = QHBoxLayout()
        eye_row.setSpacing(10)
        self.dot = StatusDot(size=10)
        eye_row.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.eyebrow = QLabel("READY · IDLE")
        self.eyebrow.setObjectName("HeroEyebrow")
        eye_row.addWidget(self.eyebrow, 0, Qt.AlignmentFlag.AlignVCenter)
        eye_row.addStretch(1)
        wrap.addLayout(eye_row)

        # editorial pull
        title = QLabel("Speak.\nIt prints.")
        title.setObjectName("HeroTitle")
        title.setTextFormat(Qt.TextFormat.PlainText)
        wrap.addWidget(title)

        lead = QLabel(
            "voxless transcribes locally with Whisper, polishes with Ollama, "
            "and types the result wherever your cursor sits — silent, private, offline."
        )
        lead.setObjectName("HeroLead")
        lead.setWordWrap(True)
        wrap.addWidget(lead)

        # hotkey panel
        hk = QFrame()
        hk.setObjectName("HeroHotkeyBox")
        hk_l = QHBoxLayout(hk)
        hk_l.setContentsMargins(28, 22, 28, 22)
        hk_l.setSpacing(28)
        meta_col = QVBoxLayout()
        meta_col.setSpacing(2)
        meta_lbl = QLabel("HOLD")
        meta_lbl.setObjectName("HeroHotkeyLabel")
        meta_col.addWidget(meta_lbl)
        self.hotkey_value = QLabel(_spec_pretty(cfg.hotkey))
        self.hotkey_value.setObjectName("HeroHotkeyValue")
        meta_col.addWidget(self.hotkey_value)
        hk_l.addLayout(meta_col, 0)
        hk_l.addStretch(1)
        # mode marker on the right
        mode_col = QVBoxLayout()
        mode_col.setSpacing(2)
        mode_label = QLabel("MODE")
        mode_label.setObjectName("HeroHotkeyLabel")
        mode_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        mode_col.addWidget(mode_label)
        self.mode_value = QLabel("PUSH-TO-TALK" if cfg.hotkey_mode == "hold" else "TAP-TO-TOGGLE")
        self.mode_value.setStyleSheet(
            f"font-family:{_mono()}; font-size:13px; color:{PAPER}; "
            f"letter-spacing:0.18em; font-weight:600;"
        )
        self.mode_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        mode_col.addWidget(self.mode_value)
        hk_l.addLayout(mode_col, 0)
        wrap.addWidget(hk)

        # vu meter
        meter_row = QHBoxLayout()
        m1 = QLabel("LEVEL")
        m1.setObjectName("HeroMetric")
        meter_row.addWidget(m1)
        meter_row.addStretch(1)
        m2 = QLabel("16 kHz · MONO")
        m2.setObjectName("HeroMetric")
        meter_row.addWidget(m2)
        wrap.addLayout(meter_row)

        self.vu = VuMeter()
        wrap.addWidget(self.vu)

        # last transcription
        last = QFrame()
        last.setObjectName("LastBox")
        ll = QVBoxLayout(last)
        ll.setContentsMargins(24, 18, 24, 22)
        ll.setSpacing(8)
        le = QLabel("LAST · WAITING")
        le.setObjectName("LastEyebrow")
        ll.addWidget(le)
        self.last_text = QLabel("— Aún no hay transcripciones. Mantén tu hotkey y empieza.")
        self.last_text.setObjectName("LastText")
        self.last_text.setWordWrap(True)
        ll.addWidget(self.last_text)
        self._last_eyebrow = le
        wrap.addWidget(last)

        wrap.addStretch(1)

    def set_state(self, state: str) -> None:
        text = STATE_TEXT.get(state, STATE_TEXT["idle"])
        if state == "idle":
            self.eyebrow.setText("READY · IDLE")
        elif state == "recording":
            self.eyebrow.setText(f"{text} · LIVE")
        elif state == "processing":
            self.eyebrow.setText(f"{text} · WHISPER + OLLAMA")
        else:
            self.eyebrow.setText(f"{text}")
        self.dot.set_state(state)
        self.vu.set_active(state == "recording")

    def set_hotkey(self, spec: str, mode: str = "hold") -> None:
        self.hotkey_value.setText(_spec_pretty(spec))
        self.mode_value.setText("PUSH-TO-TALK" if mode == "hold" else "TAP-TO-TOGGLE")

    def push_history_preview(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M")
        self._last_eyebrow.setText(f"LAST · {ts}")
        self.last_text.setText("“" + text + "”")


class GeneralPage(QWidget):
    def __init__(self, cfg: Config, on_save: Callable[[Config], None]) -> None:
        super().__init__()
        self._cfg = cfg
        self._on_save = on_save

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_page_header(
            "§ 02 · WORKSPACE",
            "General",
            "Hotkey, modo de activación y comportamiento de grabación.",
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.hotkey_recorder = HotkeyRecorder(cfg.hotkey)
        bl.addWidget(_row("01", "Hotkey",
                          "Click y presiona la tecla — o combinación — que quieres usar.",
                          self.hotkey_recorder))

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Mantener presionado · Push-to-talk", "hold")
        self.mode_combo.addItem("Tap para iniciar · tap para terminar", "toggle")
        idx = self.mode_combo.findData(cfg.hotkey_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        bl.addWidget(_row("02", "Modo de activación",
                          "Cómo se controla la grabación con la tecla.",
                          self.mode_combo))

        self.min_ms = QSpinBox()
        self.min_ms.setRange(0, 5000)
        self.min_ms.setSingleStep(50)
        self.min_ms.setSuffix(" ms")
        self.min_ms.setValue(cfg.min_record_ms)
        bl.addWidget(_row("03", "Duración mínima",
                          "Grabaciones más cortas se ignoran. Evita pulsaciones accidentales.",
                          self.min_ms))

        self.sound = QCheckBox("ENABLED")
        self.sound.setChecked(cfg.sound_feedback)
        bl.addWidget(_row("04", "Sonido al grabar",
                          "Reproducir un click sutil al iniciar y detener.",
                          self.sound))

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
        outer.addWidget(_page_header(
            "§ 04 · TRANSCRIPTION",
            "Whisper",
            "Modelo local de transcripción, vía faster-whisper / CTranslate2.",
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText(cfg.whisper.model)
        bl.addWidget(_row("01", "Modelo",
                          "Más grande = más exacto, más lento. small es el punto medio.",
                          self.model_combo))

        self.lang_edit = QLineEdit(cfg.whisper.language or "")
        self.lang_edit.setPlaceholderText("auto · es · en · fr · …")
        bl.addWidget(_row("02", "Idioma",
                          "Vacío para auto-detectar.",
                          self.lang_edit))

        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["int8", "int8_float16", "float16", "float32"])
        self.compute_combo.setCurrentText(cfg.whisper.compute_type)
        bl.addWidget(_row("03", "Precisión",
                          "int8 va bien y rápido. float16/32 piden GPU.",
                          self.compute_combo))

        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cpu"])
        self.device_combo.setCurrentText(cfg.whisper.device)
        bl.addWidget(_row("04", "Device",
                          "auto detecta GPU (Metal/CUDA) si está disponible.",
                          self.device_combo))

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
        outer.addWidget(_page_header(
            "§ 05 · COPYDESK",
            "Ollama",
            "Modelo local que limpia y puntúa el texto antes de pegarlo.",
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.enabled = QCheckBox("ENABLED")
        self.enabled.setChecked(cfg.ollama.enabled)
        bl.addWidget(_row("01", "Limpieza con Ollama",
                          "Si lo desactivas, voxless pega el texto crudo de Whisper.",
                          self.enabled))

        self.url = QLineEdit(cfg.ollama.url)
        bl.addWidget(_row("02", "URL", "URL del servidor Ollama. Local por defecto.", self.url))

        self.model = QLineEdit(cfg.ollama.model)
        self.model.setPlaceholderText("gemma3:1b · llama3.2:3b · qwen2.5:3b")
        bl.addWidget(_row("03", "Modelo",
                          "Cualquier modelo que tengas con `ollama pull`.",
                          self.model))

        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(1.0, 600.0)
        self.timeout.setDecimals(1)
        self.timeout.setSuffix(" s")
        self.timeout.setValue(cfg.ollama.timeout_s)
        bl.addWidget(_row("04", "Timeout",
                          "Si Ollama tarda más, voxless pega el texto sin limpiar.",
                          self.timeout))

        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setDecimals(2)
        self.temperature.setValue(cfg.ollama.temperature)
        bl.addWidget(_row("05", "Temperatura",
                          "0 = literal · 1 = más libre.",
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
            "§ 06 · INSTRUCTIONS",
            "Prompt",
            "Plantilla que recibe Ollama. Reglas de estilo + few-shot.",
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(48, 18, 48, 0)
        bl.setSpacing(8)

        self.editor = QPlainTextEdit()
        self.editor.setPlainText(load_prompt())
        self.editor.setMinimumHeight(360)
        bl.addWidget(self.editor, 1)

        outer.addWidget(body, 1)

        bar = QFrame()
        bar.setStyleSheet(f"background: transparent; border-top: 1px solid {RULE};")
        h = QHBoxLayout(bar)
        h.setContentsMargins(48, 18, 48, 24)
        h.addStretch(1)
        btn = QPushButton("GUARDAR PROMPT")
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
            "§ 07 · LEDGER",
            "Historial",
            "Últimas transcripciones de esta sesión (máx. 100). Doble click copia.",
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(48, 16, 48, 16)
        bl.setSpacing(12)

        self.list = QListWidget()
        self.list.setObjectName("History")
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list.itemDoubleClicked.connect(self._copy_selected)
        bl.addWidget(self.list, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        copy_btn = QPushButton("COPIAR")
        copy_btn.clicked.connect(self._copy_selected)
        clear_btn = QPushButton("LIMPIAR")
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
            display = f"{ts}    {text}\n              raw — {raw}"
        else:
            display = f"{ts}    {text}"
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
            "§ 03 · PRIVILEGES",
            "Permisos",
            "Necesarios para que voxless escuche tu hotkey y grabe el micrófono globalmente.",
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        perms = list_permissions()
        if not perms:
            note = QLabel("Tu plataforma no requiere configuración adicional.")
            note.setStyleSheet(f"color:{INK_MUTE}; padding:24px 48px; font-family:{_mono()};")
            bl.addWidget(note)
        else:
            for i, perm in enumerate(perms, start=1):
                bl.addWidget(self._build_row(f"{i:02d}", perm))

        tip_wrap = QFrame()
        tip_wrap_layout = QVBoxLayout(tip_wrap)
        tip_wrap_layout.setContentsMargins(48, 18, 48, 4)
        tip = QLabel(
            "<b>NOTA</b> — si el panel de System Settings no deja seleccionar voxless, "
            "arrastra <code>/Applications/voxless.app</code> desde Finder al panel. "
            "Tras conceder un permiso, vuelve y pulsa <i>verificar</i>."
        )
        tip.setObjectName("TipBox")
        tip.setWordWrap(True)
        tip.setTextFormat(Qt.TextFormat.RichText)
        tip.setStyleSheet(
            f"#TipBox {{ padding: 14px 16px; }}"
        )
        tip_wrap_layout.addWidget(tip)
        bl.addWidget(tip_wrap)

        outer.addWidget(_scrollable(body), 1)

        bar = QFrame()
        bar.setStyleSheet(f"background: transparent; border-top: 1px solid {RULE};")
        h = QHBoxLayout(bar)
        h.setContentsMargins(48, 14, 48, 24)
        h.addStretch(1)
        refresh = QPushButton("VERIFICAR DE NUEVO")
        refresh.clicked.connect(self.refresh)
        h.addWidget(refresh)
        outer.addWidget(bar)

    def _build_row(self, idx: str, perm: Permission) -> QWidget:
        status = QLabel("…")
        status.setMinimumWidth(110)
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        controls: list[QWidget] = [status]
        if perm.request is not None:
            req_btn = QPushButton(perm.request_label.upper())
            req_btn.setObjectName("Primary")
            req_btn.clicked.connect(self._make_request_handler(perm))
            controls.append(req_btn)
        open_btn = QPushButton("ABRIR AJUSTES")
        open_btn.clicked.connect(perm.open_settings)
        controls.append(open_btn)

        spacer = QWidget()
        spacer.setFixedSize(0, 0)
        row = _row(idx, perm.title, perm.description, spacer, extra_controls=controls)
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
        base = (
            f"font-family:{_mono()}; font-size:10px; font-weight:700;"
            f" letter-spacing:0.18em; padding:6px 12px; border-radius:3px;"
        )
        if st == "granted":
            label.setText("CONCEDIDO")
            label.setStyleSheet(base + f" color:#15803d; background:rgba(16,185,129,0.14);")
        elif st == "denied":
            label.setText("FALTA")
            label.setStyleSheet(base + f" color:{PEAK}; background:rgba(220,38,38,0.12);")
        else:
            label.setText("—")
            label.setStyleSheet(base + f" color:{INK_MUTE}; background:rgba(122,113,106,0.10);")

    def refresh(self) -> None:
        for perm, lbl in self._rows:
            self._render(perm, lbl)


# ─── main window ────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    config_changed = Signal(object)
    prompt_changed = Signal(str)
    quit_requested = Signal()

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.setWindowTitle("voxless")
        self.setMinimumSize(QSize(960, 660))
        self.resize(QSize(1040, 720))
        self._cfg = cfg

        root = QWidget()
        root.setObjectName("Root")
        rl = QHBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # ── sidebar ──────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(232)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(0)

        brand = QLabel("voxless.")
        brand.setObjectName("SidebarBrand")
        side.addWidget(brand)
        tag = QLabel("STUDIO PRESS · MMVI")
        tag.setObjectName("SidebarTagline")
        side.addWidget(tag)

        sec = QLabel("§ INDEX")
        sec.setObjectName("SidebarSection")
        side.addWidget(sec)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        for i, (_key, label) in enumerate(NAV_ITEMS, start=1):
            item = QListWidgetItem(f"{i:02d}    {label}")
            item.setSizeHint(QSize(0, 30))
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)
        side.addWidget(self.nav, 1)

        version_lbl = QLabel("v 0.1.6 · LOCAL")
        version_lbl.setObjectName("VersionFooter")
        side.addWidget(version_lbl)

        rl.addWidget(sidebar)

        # ── content area ─────────────────────────────────────────────
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

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
        cl.addWidget(self.stack, 1)

        rl.addWidget(content, 1)
        self.setCentralWidget(root)

        self._apply_qss()

    def _on_nav_change(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        if self.stack.currentWidget() is self.permissions_page:
            self.permissions_page.refresh()

    def _apply_qss(self) -> None:
        self.setStyleSheet(QSS_DARK() if _is_dark_mode() else QSS_LIGHT())

    def _handle_config_save(self, cfg: Config) -> None:
        try:
            save_config(cfg)
        except Exception as exc:
            log.exception("Failed to save config")
            self.show_toast(f"NO SE PUDO GUARDAR · {exc}", variant="error")
            return
        self.home_page.set_hotkey(cfg.hotkey, cfg.hotkey_mode)
        self.config_changed.emit(cfg)
        self.show_toast("CONFIGURACIÓN GUARDADA")

    def _handle_prompt_save(self, text: str) -> None:
        try:
            save_prompt(text)
        except Exception as exc:
            log.exception("Failed to save prompt")
            self.show_toast(f"NO SE PUDO GUARDAR · {exc}", variant="error")
            return
        self.prompt_changed.emit(text)
        self.show_toast("PROMPT GUARDADO")

    def show_toast(self, text: str, variant: str = "success") -> None:
        toast = Toast(text, variant=variant, parent=self)  # type: ignore[arg-type]
        toast.show_for(self)

    def set_state(self, state: str) -> None:
        self.home_page.set_state(state)

    def push_audio_peak(self, peak: float) -> None:
        self.home_page.vu.push(peak)

    def push_history(self, raw: str, clean: str) -> None:
        self.history_page.push(raw, clean)
        self.home_page.push_history_preview(clean if clean else raw)

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
