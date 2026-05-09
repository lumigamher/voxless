"""voxless main window — Nothing-inspired design system.

Pure monochrome (black + white) + Nothing red accent. Sharp corners,
dot-grid background, industrial numbering, mono typography throughout.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime

import numpy as np
from PySide6.QtCore import (
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontDatabase,
    QKeyEvent,
    QPainter,
    QPen,
    QPixmap,
)
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

from . import ai_actions
from .config import Config, save_config, save_prompt
from .i18n import t, set_lang
from .permissions import Permission, list_permissions
from .prompts import load_prompt
from .toast import Toast

log = logging.getLogger(__name__)

# ── design tokens — Nothing palette ──────────────────────────────────────
BG          = "#000000"
SURFACE     = "#0a0a0a"
SURFACE_HI  = "#141414"
HAIRLINE    = "#1f1f1f"
BORDER      = "#2a2a2a"
INK         = "#ffffff"
INK_DIM     = "#a3a3a3"
INK_MUTE    = "#525252"
ACCENT      = "#ff3636"
ACCENT_TINT = "rgba(255, 54, 54, 0.14)"
SUCCESS     = "#5fdb5f"
AMBER       = "#ffaa00"


def _serif() -> str:
    return '"Iowan Old Style", "Charter", "Georgia", serif'


def _mono() -> str:
    return '"SF Mono", "Menlo", "JetBrains Mono", "Cascadia Mono", "Consolas", monospace'


def _sans() -> str:
    return '-apple-system, "SF Pro Text", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif'


def _is_dark_mode() -> bool:
    return True  # Nothing aesthetic is always dark


# ── inline button stylesheets ─────────────────────────────────────────────

_PRIMARY_BTN_QSS = f"""
QPushButton {{
    background-color: {INK};
    color: {BG};
    border: 1px solid {INK};
    border-radius: 2px;
    padding: 11px 22px;
    font-family: {_mono()};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}}
QPushButton:hover {{
    background-color: {ACCENT};
    color: {INK};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: #c4292c;
    color: {INK};
    border-color: #c4292c;
}}
QPushButton:disabled {{
    background-color: {SURFACE_HI};
    color: {INK_MUTE};
    border-color: {BORDER};
}}
"""

_DEFAULT_BTN_QSS = f"""
QPushButton {{
    background-color: transparent;
    color: {INK};
    border: 1px solid {BORDER};
    border-radius: 2px;
    padding: 11px 20px;
    font-family: {_mono()};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.10em;
    text-transform: uppercase;
}}
QPushButton:hover {{
    background-color: {SURFACE_HI};
    color: {INK};
    border-color: {INK};
}}
QPushButton:pressed {{
    background-color: {SURFACE};
    color: {INK};
}}
"""


def primary_btn(label: str, on_click: Callable[[], None] | None = None) -> QPushButton:
    btn = QPushButton(label.upper())
    btn.setStyleSheet(_PRIMARY_BTN_QSS)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click:
        btn.clicked.connect(on_click)
    return btn


def default_btn(label: str, on_click: Callable[[], None] | None = None) -> QPushButton:
    btn = QPushButton(label.upper())
    btn.setStyleSheet(_DEFAULT_BTN_QSS)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click:
        btn.clicked.connect(on_click)
    return btn


# ── global QSS ───────────────────────────────────────────────────────────

def QSS_NOTHING() -> str:
    return f"""
QWidget {{ font-family: {_sans()}; color: {INK}; background: transparent; }}

QMainWindow, #Root {{ background-color: {BG}; }}

/* ── sidebar ───────────────────────────────────────────────────── */
#Sidebar {{
  background-color: {BG};
  border-right: 1px solid {HAIRLINE};
}}
#SidebarBrand {{
  font-family: {_mono()};
  font-size: 22px;
  font-weight: 800;
  color: {INK};
  letter-spacing: 0.04em;
  padding: 26px 24px 0 24px;
}}
#SidebarTagline {{
  font-family: {_mono()};
  font-size: 9px;
  color: {INK_MUTE};
  letter-spacing: 0.20em;
  padding: 4px 24px 22px 24px;
  text-transform: uppercase;
}}
#SidebarSection {{
  font-family: {_mono()};
  color: {INK_MUTE};
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.22em;
  padding: 12px 24px 8px 24px;
  text-transform: uppercase;
}}
QListWidget#NavList {{
  background: transparent; border: none; outline: 0;
}}
QListWidget#NavList::item {{
  padding: 9px 16px 9px 22px;
  margin: 0;
  color: {INK_DIM};
  border-left: 2px solid transparent;
  font-family: {_mono()};
  font-size: 12px;
  letter-spacing: 0.02em;
}}
QListWidget#NavList::item:selected {{
  color: {INK};
  border-left-color: {ACCENT};
  background: {SURFACE};
  font-weight: 700;
}}
QListWidget#NavList::item:hover:!selected {{
  color: {INK};
  background: {SURFACE};
}}
#VersionFooter {{
  font-family: {_mono()};
  color: {INK_MUTE};
  font-size: 9px;
  letter-spacing: 0.18em;
  padding: 14px 24px 18px 24px;
  text-transform: uppercase;
}}

/* ── page header ─────────────────────────────────────────────── */
#PageHeader {{ background: transparent; border-bottom: 1px solid {HAIRLINE}; }}
QLabel#PageEyebrow {{
  font-family: {_mono()};
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.26em;
  color: {ACCENT};
  text-transform: uppercase;
}}
QLabel#PageTitle {{
  font-family: {_mono()};
  font-size: 32px;
  font-weight: 800;
  color: {INK};
  letter-spacing: 0.02em;
}}
QLabel#PageSub {{
  font-family: {_sans()};
  font-size: 13px;
  color: {INK_DIM};
}}

/* ── settings rows ───────────────────────────────────────────── */
QFrame#Row {{ border-bottom: 1px solid {HAIRLINE}; background: transparent; }}
QLabel#RowIndex {{
  font-family: {_mono()};
  font-size: 10px;
  color: {INK_MUTE};
  letter-spacing: 0.18em;
  font-weight: 700;
}}
QLabel#RowTitle {{
  font-family: {_mono()};
  font-size: 13px;
  font-weight: 700;
  color: {INK};
  letter-spacing: 0.04em;
  text-transform: uppercase;
}}
QLabel#RowDesc {{
  font-family: {_sans()};
  font-size: 12px;
  color: {INK_DIM};
}}

/* ── inputs ───────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
  background-color: {SURFACE_HI};
  color: {INK};
  border: 1px solid {BORDER};
  border-radius: 2px;
  padding: 9px 12px;
  selection-background-color: {ACCENT};
  selection-color: {INK};
  font-family: {_mono()};
  font-size: 12px;
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QPlainTextEdit:hover {{ border-color: {INK_DIM}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: 0; width: 22px; }}

/* ── checkboxes ──────────────────────────────────────────────── */
QCheckBox {{
  color: {INK_DIM};
  font-family: {_mono()};
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.10em;
  spacing: 10px;
}}
QCheckBox::indicator {{
  width: 16px; height: 16px;
  border: 1px solid {BORDER}; border-radius: 0;
  background: transparent;
}}
QCheckBox::indicator:hover {{ border-color: {INK_DIM}; }}
QCheckBox::indicator:checked {{
  background: {ACCENT}; border-color: {ACCENT};
  image: none;
}}

/* ── history list ────────────────────────────────────────────── */
QListWidget#History {{
  background: {SURFACE};
  border: 1px solid {HAIRLINE};
  border-radius: 2px;
  outline: 0;
  padding: 0;
}}
QListWidget#History::item {{
  background: transparent;
  border-bottom: 1px solid {HAIRLINE};
  border-radius: 0;
  padding: 14px 18px;
  color: {INK};
  font-family: {_mono()};
  font-size: 12px;
}}
QListWidget#History::item:hover {{ background: {SURFACE_HI}; }}
QListWidget#History::item:selected {{
  background: {ACCENT_TINT};
  color: {INK};
}}

/* ── scrollbar ───────────────────────────────────────────────── */
QScrollBar:vertical {{
  background: transparent; width: 8px; margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
  background: {BORDER}; border-radius: 0; min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {INK_MUTE}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

/* ── hero / overlays ─────────────────────────────────────────── */
#HeroFrame {{ background: transparent; }}
QLabel#HeroEyebrow {{
  font-family: {_mono()};
  font-size: 10px;
  letter-spacing: 0.26em;
  font-weight: 700;
  color: {ACCENT};
  text-transform: uppercase;
}}
QLabel#HeroTitle {{
  font-family: {_mono()};
  font-size: 56px;
  font-weight: 800;
  color: {INK};
  letter-spacing: 0.01em;
  line-height: 1;
}}
QLabel#HeroLead {{
  font-family: {_sans()};
  font-size: 14px;
  color: {INK_DIM};
  line-height: 22px;
}}
#HeroHotkeyBox {{
  background: {SURFACE};
  border: 1px solid {BORDER};
  border-radius: 2px;
}}
QLabel#HeroHotkeyLabel {{
  font-family: {_mono()};
  font-size: 9px;
  color: {INK_MUTE};
  letter-spacing: 0.26em;
  text-transform: uppercase;
}}
QLabel#HeroHotkeyValue {{
  font-family: {_mono()};
  font-size: 32px;
  font-weight: 800;
  color: {INK};
  letter-spacing: 0.02em;
}}
QLabel#HeroMetric {{
  font-family: {_mono()};
  font-size: 9px;
  color: {INK_MUTE};
  letter-spacing: 0.22em;
  text-transform: uppercase;
}}

#LastBox {{
  background: {SURFACE};
  border: 1px solid {HAIRLINE};
  border-radius: 2px;
}}
QLabel#LastEyebrow {{
  font-family: {_mono()};
  font-size: 10px;
  color: {INK_MUTE};
  letter-spacing: 0.22em;
  font-weight: 700;
  text-transform: uppercase;
}}
QLabel#LastText {{
  font-family: {_mono()};
  font-size: 13px;
  color: {INK};
  line-height: 22px;
}}

#TipBox {{
  background: {SURFACE};
  border: 1px solid {HAIRLINE};
  border-radius: 2px;
  font-family: {_mono()};
  font-size: 11px;
  color: {INK_DIM};
}}
"""


# ─── data ────────────────────────────────────────────────────────────────

def NAV_ITEMS() -> list[tuple[str, str]]:
    return [
        ("home",        t("nav.home")),
        ("general",     t("nav.general")),
        ("permissions", t("nav.permissions")),
        ("whisper",     t("nav.whisper")),
        ("ollama",      t("nav.ollama")),
        ("prompt",      t("nav.prompt")),
        ("history",     t("nav.history")),
    ]

STATE_TEXT = {
    "idle":       "READY",
    "recording":  "REC",
    "processing": "WRITE",
    "error":      "ERR",
}

STATE_DOT_COLOR = {
    "idle": SUCCESS,
    "recording": ACCENT,
    "processing": AMBER,
    "error": ACCENT,
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
            if mapped: return mapped
        elif sys.platform.startswith("win"):
            mapped = _WIN_VK_TO_NAME.get(nv)
            if mapped: return mapped
        if key == Qt.Key.Key_Alt: return "alt"
        if key == Qt.Key.Key_Control: return "ctrl"
        if key == Qt.Key.Key_Meta: return "cmd" if sys.platform == "darwin" else "ctrl"
        if key == Qt.Key.Key_Shift: return "shift"
    if event.text() and len(event.text()) == 1 and event.text().strip():
        ch = event.text().lower()
        if ch.isalnum(): return ch
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
        "space": "SPC", "tab": "TAB", "esc": "ESC",
        "caps_lock": "CAPS", "fn": "FN",
    }
    out = []
    for p in parts:
        if p in label_map: out.append(label_map[p])
        elif p.startswith("f") and p[1:].isdigit(): out.append(p.upper())
        else: out.append(p.upper())
    return "·".join(out)


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
            self.setText("● PRESS · ESC TO CANCEL")
            self.setStyleSheet(
                f"QPushButton {{ background:{ACCENT}; color:{INK}; "
                f"border:1px solid {ACCENT}; border-radius:2px; padding:11px 22px; "
                f"font-family:{_mono()}; font-size:10px; font-weight:800; "
                f"letter-spacing:0.18em; text-transform:uppercase; }}"
            )
        else:
            self.setText(_spec_pretty(self._spec))
            self.setStyleSheet(_DEFAULT_BTN_QSS)

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
        if mods & Qt.KeyboardModifier.ControlModifier and name not in ("ctrl", "ctrl_l", "ctrl_r"): ms.append("ctrl")
        if mods & Qt.KeyboardModifier.AltModifier and name not in ("alt", "left_option", "right_option"): ms.append("alt")
        if mods & Qt.KeyboardModifier.MetaModifier and name not in ("cmd", "cmd_l", "cmd_r"): ms.append("cmd")
        if mods & Qt.KeyboardModifier.ShiftModifier and name not in ("shift", "shift_l", "shift_r"): ms.append("shift")
        spec = "+".join(f"<{x}>" for x in ms) + "+" + name if ms else name
        self._spec = spec
        self._recording = False
        self.releaseKeyboard()
        self._update()
        self.captured.emit(spec)


# ─── decoration widgets ─────────────────────────────────────────────────

class DotGridBg(QWidget):
    """Subtle dot-grid pattern as a low-key Nothing texture."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        color = QColor("#1a1a1a")
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        spacing = 24
        radius = 1
        for y in range(spacing, self.height(), spacing):
            for x in range(spacing, self.width(), spacing):
                p.drawRect(x - radius, y - radius, radius * 2, radius * 2)


class StatusDot(QWidget):
    def __init__(self, size: int = 12) -> None:
        super().__init__()
        self.setFixedSize(size, size)
        self._color = QColor(STATE_DOT_COLOR["idle"])
        self._pulse = 0.0
        self._dir = 1.0
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
        self._pulse += 0.07 * self._dir
        if self._pulse >= 1.0: self._pulse = 1.0; self._dir = -1.0
        elif self._pulse <= 0.0: self._pulse = 0.0; self._dir = 1.0
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        # Square LED dot (Nothing-style — pixel grid)
        if self._timer.isActive():
            halo = QColor(self._color); halo.setAlphaF(0.30 * self._pulse)
            p.setBrush(halo); p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(self.rect())
        p.setBrush(self._color); p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect().adjusted(2, 2, -2, -2))


class GlyphMeter(QWidget):
    """LED-pixel-grid VU meter — Nothing's signature aesthetic."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._levels: list[float] = [0.0] * 32
        self._active = False

    def push(self, peak: float) -> None:
        self._levels = self._levels[1:] + [min(1.0, peak * 6.5)]
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._levels = [0.0] * 32
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()
        n = len(self._levels)
        bar_w = max(4, (w - 16) // n - 4)
        gap = 4
        # rows of pixel-LED segments (Nothing glyph aesthetic)
        rows = 7
        cell = max(3, h // rows - 2)

        total_w = n * (bar_w + gap) - gap
        start_x = (w - total_w) // 2

        x = start_x
        for level in self._levels:
            lit_rows = int(level * rows)
            for r in range(rows):
                y = h - (r + 1) * (cell + 1) - 4
                if r < lit_rows:
                    # Color shifts to red at peak
                    if r >= rows - 2 and self._active:
                        color = QColor(ACCENT)
                    else:
                        color = QColor(INK) if self._active else QColor(BORDER)
                    color.setAlphaF(1.0 if self._active else 0.6)
                else:
                    color = QColor(HAIRLINE)
                p.setBrush(color); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(x, y, bar_w, cell)
            x += bar_w + gap


# ─── building blocks ────────────────────────────────────────────────────

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
    idx.setFixedWidth(40)
    idx.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    layout.addWidget(idx, 0)

    text_col = QVBoxLayout()
    text_col.setSpacing(4)
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
    bar.setStyleSheet(f"background: transparent; border-top: 1px solid {HAIRLINE};")
    h = QHBoxLayout(bar)
    h.setContentsMargins(48, 18, 48, 24)
    h.addStretch(1)
    h.addWidget(primary_btn("Save", on_save))
    return bar


# ─── pages ─────────────────────────────────────────────────────────────

class HomePage(QWidget):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self._cfg = cfg
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(48, 40, 48, 40)
        wrap.setSpacing(24)

        # eyebrow with glyph dot
        eye_row = QHBoxLayout()
        eye_row.setSpacing(10)
        self.dot = StatusDot(size=12)
        eye_row.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.eyebrow = QLabel(t("hero.ready_idle"))
        self.eyebrow.setObjectName("HeroEyebrow")
        eye_row.addWidget(self.eyebrow, 0, Qt.AlignmentFlag.AlignVCenter)
        eye_row.addStretch(1)
        meta = QLabel("ver 0.3.0")
        meta.setObjectName("HeroMetric")
        eye_row.addWidget(meta, 0, Qt.AlignmentFlag.AlignVCenter)
        wrap.addLayout(eye_row)

        # display title
        title = QLabel(t("hero.title"))
        title.setObjectName("HeroTitle")
        title.setTextFormat(Qt.TextFormat.PlainText)
        wrap.addWidget(title)

        lead = QLabel(t("hero.lead"))
        lead.setObjectName("HeroLead")
        lead.setWordWrap(True)
        wrap.addWidget(lead)

        # hotkey panel
        hk = QFrame()
        hk.setObjectName("HeroHotkeyBox")
        hk_l = QHBoxLayout(hk)
        hk_l.setContentsMargins(28, 24, 28, 24)
        hk_l.setSpacing(28)
        meta_col = QVBoxLayout()
        meta_col.setSpacing(4)
        meta_lbl = QLabel(t("hero.hotkey"))
        meta_lbl.setObjectName("HeroHotkeyLabel")
        meta_col.addWidget(meta_lbl)
        self.hotkey_value = QLabel(_spec_pretty(cfg.hotkey))
        self.hotkey_value.setObjectName("HeroHotkeyValue")
        meta_col.addWidget(self.hotkey_value)
        hk_l.addLayout(meta_col, 0)
        hk_l.addStretch(1)
        # mode marker
        mode_col = QVBoxLayout()
        mode_col.setSpacing(4)
        mode_label = QLabel(t("hero.mode"))
        mode_label.setObjectName("HeroHotkeyLabel")
        mode_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        mode_col.addWidget(mode_label)
        self.mode_value = QLabel(t("hero.mode.hold") if cfg.hotkey_mode == "hold" else t("hero.mode.toggle"))
        self.mode_value.setStyleSheet(
            f"font-family:{_mono()}; font-size:14px; color:{INK}; "
            f"letter-spacing:0.18em; font-weight:800; text-transform:uppercase;"
        )
        self.mode_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        mode_col.addWidget(self.mode_value)
        hk_l.addLayout(mode_col, 0)
        wrap.addWidget(hk)

        # vu meter row
        meter_row = QHBoxLayout()
        m1 = QLabel(t("hero.level"))
        m1.setObjectName("HeroMetric")
        meter_row.addWidget(m1)
        meter_row.addStretch(1)
        m2 = QLabel("16k · MONO")
        m2.setObjectName("HeroMetric")
        meter_row.addWidget(m2)
        wrap.addLayout(meter_row)

        self.vu = GlyphMeter()
        wrap.addWidget(self.vu)

        # last
        last = QFrame()
        last.setObjectName("LastBox")
        ll = QVBoxLayout(last)
        ll.setContentsMargins(24, 20, 24, 22)
        ll.setSpacing(10)
        le = QLabel(t("hero.last.waiting"))
        le.setObjectName("LastEyebrow")
        ll.addWidget(le)
        self.last_text = QLabel(t("hero.last.empty"))
        self.last_text.setObjectName("LastText")
        self.last_text.setWordWrap(True)
        ll.addWidget(self.last_text)
        self._last_eyebrow = le
        wrap.addWidget(last)

        wrap.addStretch(1)

    def set_state(self, state: str) -> None:
        if state == "idle":
            self.eyebrow.setText(t("hero.ready_idle"))
        elif state == "recording":
            self.eyebrow.setText(t("hero.rec_live"))
        elif state == "processing":
            self.eyebrow.setText(t("hero.processing"))
        else:
            self.eyebrow.setText(STATE_TEXT.get(state, "ERROR"))
        self.dot.set_state(state)
        self.vu.set_active(state == "recording")

    def set_hotkey(self, spec: str, mode: str = "hold") -> None:
        self.hotkey_value.setText(_spec_pretty(spec))
        self.mode_value.setText(t("hero.mode.hold") if mode == "hold" else t("hero.mode.toggle"))

    def push_history_preview(self, text_str: str) -> None:
        ts = datetime.now().strftime("%H:%M")
        self._last_eyebrow.setText(t("hero.last.template", time=ts))
        self.last_text.setText(text_str)


class GeneralPage(QWidget):
    def __init__(self, cfg: Config, on_save: Callable[[Config], None]) -> None:
        super().__init__()
        self._cfg = cfg
        self._on_save = on_save

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_page_header(
            t("page.general.eyebrow"),
            t("page.general.title"),
            t("page.general.sub"),
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.hotkey_recorder = HotkeyRecorder(cfg.hotkey)
        bl.addWidget(_row("01", t("general.hotkey.title"),
                          t("general.hotkey.desc"),
                          self.hotkey_recorder))

        self.mode_combo = QComboBox()
        self.mode_combo.addItem(t("general.activation.hold"), "hold")
        self.mode_combo.addItem(t("general.activation.toggle"), "toggle")
        idx = self.mode_combo.findData(cfg.hotkey_mode)
        if idx >= 0: self.mode_combo.setCurrentIndex(idx)
        bl.addWidget(_row("02", t("general.activation.title"),
                          t("general.activation.desc"),
                          self.mode_combo))

        self.min_ms = QSpinBox()
        self.min_ms.setRange(0, 5000)
        self.min_ms.setSingleStep(50)
        self.min_ms.setSuffix(" MS")
        self.min_ms.setValue(cfg.min_record_ms)
        bl.addWidget(_row("03", t("general.minduration.title"),
                          t("general.minduration.desc"),
                          self.min_ms))

        self.sound = QCheckBox(t("general.checkbox.enabled"))
        self.sound.setChecked(cfg.sound_feedback)
        bl.addWidget(_row("04", t("general.sound.title"),
                          t("general.sound.desc"),
                          self.sound))

        self.overlay_chk = QCheckBox(t("general.checkbox.enabled"))
        self.overlay_chk.setChecked(cfg.show_overlay)
        bl.addWidget(_row("05", t("general.overlay.title"),
                          t("general.overlay.desc"),
                          self.overlay_chk))

        self.lang_combo = QComboBox()
        self.lang_combo.addItem(t("general.lang.es"), "es")
        self.lang_combo.addItem(t("general.lang.en"), "en")
        idx = self.lang_combo.findData(cfg.ui_language)
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        bl.addWidget(_row("06", t("general.lang.title"),
                          t("general.lang.desc"),
                          self.lang_combo))

        outer.addWidget(_scrollable(body), 1)
        outer.addWidget(_save_bar(self._save))

    def _save(self) -> None:
        self._cfg.hotkey = self.hotkey_recorder.spec().strip() or "right_option"
        self._cfg.hotkey_mode = self.mode_combo.currentData()
        self._cfg.min_record_ms = int(self.min_ms.value())
        self._cfg.sound_feedback = self.sound.isChecked()
        self._cfg.show_overlay = self.overlay_chk.isChecked()
        self._cfg.ui_language = self.lang_combo.currentData()
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
            t("page.whisper.eyebrow"),
            t("page.whisper.title"),
            t("page.whisper.sub"),
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText(cfg.whisper.model)
        bl.addWidget(_row("01", t("whisper.model.title"),
                          t("whisper.model.desc"),
                          self.model_combo))

        self.lang_edit = QLineEdit(cfg.whisper.language or "")
        self.lang_edit.setPlaceholderText(t("whisper.lang.placeholder"))
        bl.addWidget(_row("02", t("whisper.lang.title"),
                          t("whisper.lang.desc"),
                          self.lang_edit))

        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["int8", "int8_float16", "float16", "float32"])
        self.compute_combo.setCurrentText(cfg.whisper.compute_type)
        bl.addWidget(_row("03", t("whisper.precision.title"),
                          t("whisper.precision.desc"),
                          self.compute_combo))

        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cpu"])
        self.device_combo.setCurrentText(cfg.whisper.device)
        bl.addWidget(_row("04", t("whisper.device.title"),
                          t("whisper.device.desc"),
                          self.device_combo))

        outer.addWidget(_scrollable(body), 1)
        outer.addWidget(_save_bar(self._save))

    def _save(self) -> None:
        self._cfg.whisper.model = self.model_combo.currentText()
        self._cfg.whisper.language = self.lang_edit.text().strip() or None
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
            t("page.ollama.eyebrow"),
            t("page.ollama.title"),
            t("page.ollama.sub"),
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.enabled = QCheckBox(t("general.checkbox.enabled"))
        self.enabled.setChecked(cfg.ollama.enabled)
        bl.addWidget(_row("01", t("ollama.enabled.title"),
                          t("ollama.enabled.desc"),
                          self.enabled))

        self.url = QLineEdit(cfg.ollama.url)
        bl.addWidget(_row("02", t("ollama.url.title"), t("ollama.url.desc"), self.url))

        self.model = QLineEdit(cfg.ollama.model)
        self.model.setPlaceholderText("gemma3:1b · llama3.2:3b · qwen2.5:3b")
        bl.addWidget(_row("03", t("ollama.model.title"),
                          t("ollama.model.desc"),
                          self.model))

        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(1.0, 600.0)
        self.timeout.setDecimals(1)
        self.timeout.setSuffix(" S")
        self.timeout.setValue(cfg.ollama.timeout_s)
        bl.addWidget(_row("04", t("ollama.timeout.title"),
                          t("ollama.timeout.desc"),
                          self.timeout))

        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setDecimals(2)
        self.temperature.setValue(cfg.ollama.temperature)
        bl.addWidget(_row("05", t("ollama.temperature.title"),
                          t("ollama.temperature.desc"),
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
            t("page.prompt.eyebrow"),
            t("page.prompt.title"),
            t("page.prompt.sub"),
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
        bar.setStyleSheet(f"background: transparent; border-top: 1px solid {HAIRLINE};")
        h = QHBoxLayout(bar)
        h.setContentsMargins(48, 18, 48, 24)
        h.addStretch(1)
        h.addWidget(primary_btn(t("btn.save_prompt"),
                                lambda: self._on_save(self.editor.toPlainText())))
        outer.addWidget(bar)


class HistoryPage(QWidget):
    ai_action_requested = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_page_header(
            t("page.history.eyebrow"),
            t("page.history.title"),
            t("page.history.sub"),
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(48, 16, 48, 16)
        bl.setSpacing(12)

        self.list = QListWidget()
        self.list.setObjectName("History")
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list.itemDoubleClicked.connect(self._copy_selected)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._open_context_menu)
        bl.addWidget(self.list, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(default_btn(t("btn.copy"), self._copy_selected))
        ai_btn = primary_btn(t("btn.ai_actions"))
        ai_btn.clicked.connect(lambda: self._open_ai_menu(ai_btn))
        actions.addWidget(ai_btn)
        actions.addWidget(default_btn(t("btn.clear"), self.list.clear))
        bl.addLayout(actions)

        outer.addWidget(body, 1)

    def _menu_qss(self) -> str:
        return f"""
            QMenu {{
                background: {SURFACE};
                color: {INK};
                border: 1px solid {BORDER};
                border-radius: 0;
                padding: 4px;
                font-family: {_mono()};
                font-size: 11px;
            }}
            QMenu::item {{ padding: 9px 16px; border-radius: 0; letter-spacing:0.05em; }}
            QMenu::item:selected {{ background: {ACCENT}; color: {INK}; }}
            QMenu::separator {{ height: 1px; background: {HAIRLINE}; margin: 4px 8px; }}
        """

    def _open_ai_menu(self, anchor: QWidget) -> None:
        from PySide6.QtWidgets import QMenu
        if not self.list.currentItem(): return
        menu = QMenu(self); menu.setStyleSheet(self._menu_qss())
        for action in ai_actions.ALL:
            ma = menu.addAction(action.label.upper())
            ma.triggered.connect(lambda _c=False, a=action: self._dispatch(a))
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _open_context_menu(self, point) -> None:
        item = self.list.itemAt(point)
        if item is None: return
        self.list.setCurrentItem(item)
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self); menu.setStyleSheet(self._menu_qss())
        copy_act = menu.addAction("COPY")
        copy_act.triggered.connect(self._copy_selected)
        menu.addSeparator()
        for action in ai_actions.ALL:
            ma = menu.addAction(action.label.upper())
            ma.triggered.connect(lambda _c=False, a=action: self._dispatch(a))
        menu.exec(self.list.viewport().mapToGlobal(point))

    def _dispatch(self, action) -> None:
        item = self.list.currentItem()
        if not item: return
        text = item.data(Qt.ItemDataRole.UserRole) or item.text()
        self.ai_action_requested.emit(text, action)

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
        if not item: return
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
            t("page.permissions.eyebrow"),
            t("page.permissions.title"),
            t("page.permissions.sub"),
        ))

        body = QFrame()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        perms = list_permissions()
        if not perms:
            note = QLabel("No platform permissions required.")
            note.setStyleSheet(f"color:{INK_DIM}; padding:24px 48px; font-family:{_mono()};")
            bl.addWidget(note)
        else:
            for i, perm in enumerate(perms, start=1):
                bl.addWidget(self._build_row(f"{i:02d}", perm))

        tip_wrap = QFrame()
        tip_wrap_layout = QVBoxLayout(tip_wrap)
        tip_wrap_layout.setContentsMargins(48, 18, 48, 4)
        tip = QLabel(t("perm.tip"))
        tip.setObjectName("TipBox")
        tip.setWordWrap(True)
        tip.setTextFormat(Qt.TextFormat.RichText)
        tip.setStyleSheet("#TipBox { padding: 14px 16px; }")
        tip_wrap_layout.addWidget(tip)
        bl.addWidget(tip_wrap)

        outer.addWidget(_scrollable(body), 1)

        bar = QFrame()
        bar.setStyleSheet(f"background: transparent; border-top: 1px solid {HAIRLINE};")
        h = QHBoxLayout(bar)
        h.setContentsMargins(48, 14, 48, 24)
        h.addStretch(1)
        h.addWidget(default_btn(t("btn.verify"), self.refresh))
        outer.addWidget(bar)

    def _build_row(self, idx: str, perm: Permission) -> QWidget:
        status = QLabel("…")
        status.setMinimumWidth(110)
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls: list[QWidget] = [status]
        if perm.request is not None:
            controls.append(primary_btn(perm.request_label, self._make_request_handler(perm)))
        controls.append(default_btn(t("btn.settings"), perm.open_settings))

        spacer = QWidget()
        spacer.setFixedSize(0, 0)
        row = _row(idx, perm.title.upper(), perm.description, spacer, extra_controls=controls)
        self._rows.append((perm, status))
        self._render(perm, status)
        return row

    def _make_request_handler(self, perm: Permission):
        def handler() -> None:
            try:
                if perm.request: perm.request()
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
            f"font-family:{_mono()}; font-size:10px; font-weight:800;"
            f" letter-spacing:0.20em; padding:7px 12px; border-radius:0;"
            f" border:1px solid;"
        )
        if st == "granted":
            label.setText(t("perm.granted"))
            label.setStyleSheet(base + f" color:{SUCCESS}; background:rgba(95,219,95,0.12);"
                                       f" border-color:{SUCCESS};")
        elif st == "denied":
            label.setText(t("perm.missing"))
            label.setStyleSheet(base + f" color:{ACCENT}; background:rgba(255,54,54,0.10);"
                                       f" border-color:{ACCENT};")
        else:
            label.setText(t("perm.unknown"))
            label.setStyleSheet(base + f" color:{INK_DIM}; background:transparent;"
                                       f" border-color:{BORDER};")

    def refresh(self) -> None:
        for perm, lbl in self._rows:
            self._render(perm, lbl)


# ─── main window ────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    config_changed = Signal(object)
    prompt_changed = Signal(str)
    quit_requested = Signal()

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        # Hard guard: the window can only become visible when explicitly
        # authorized via show_authorized(). Any other show() call (Qt's
        # auto-show, NSApplicationDelegate's applicationShouldHandleReopen,
        # focus events, etc) is silently ignored.
        self._show_authorized = False
        self.setWindowTitle("voxless")
        self.setMinimumSize(QSize(960, 660))
        self.resize(QSize(1040, 720))
        self._cfg = cfg

        root = QWidget()
        root.setObjectName("Root")
        rl = QHBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # ── sidebar ──────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(232)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(0)

        brand = QLabel("voxless")
        brand.setObjectName("SidebarBrand")
        side.addWidget(brand)
        tag = QLabel(t("side.tagline"))
        tag.setObjectName("SidebarTagline")
        side.addWidget(tag)

        sec = QLabel(t("side.section"))
        sec.setObjectName("SidebarSection")
        side.addWidget(sec)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        for i, (_key, label) in enumerate(NAV_ITEMS(), start=1):
            item = QListWidgetItem(f"{i:03d}    {label}")
            item.setSizeHint(QSize(0, 34))
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)
        side.addWidget(self.nav, 1)

        version_lbl = QLabel(f"v 0.3.0 · {t('side.versionsuffix')}")
        version_lbl.setObjectName("VersionFooter")
        side.addWidget(version_lbl)

        rl.addWidget(sidebar)

        # ── content area ─────────────────────────────────────
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
        self.setStyleSheet(QSS_NOTHING())

    def _handle_config_save(self, cfg: Config) -> None:
        try:
            save_config(cfg)
        except Exception as exc:
            log.exception("Failed to save config")
            self.show_toast(t("toast.save_failed", error=str(exc)), variant="error")
            return
        # If language changed, swap i18n + re-apply UI text where we
        # can without rebuilding everything.
        if cfg.ui_language != self._cfg.ui_language:
            set_lang(cfg.ui_language)
            self._cfg = cfg
            self._refresh_text()
        else:
            self._cfg = cfg
        self.home_page.set_hotkey(cfg.hotkey, cfg.hotkey_mode)
        self.config_changed.emit(cfg)
        self.show_toast(t("toast.saved.config"))

    def _refresh_text(self) -> None:
        """Re-render text after a language switch."""
        self.show_toast(t("toast.saved.config"), variant="info")

    def _handle_prompt_save(self, text_str: str) -> None:
        try:
            save_prompt(text_str)
        except Exception as exc:
            log.exception("Failed to save prompt")
            self.show_toast(t("toast.save_failed", error=str(exc)), variant="error")
            return
        self.prompt_changed.emit(text_str)
        self.show_toast(t("toast.saved.prompt"))

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

    def show_authorized(self) -> None:
        """The ONLY sanctioned way to make this window visible."""
        self._show_authorized = True
        if hasattr(self, "_user_opened_flag"):
            self._user_opened_flag["flag"] = True
        super().show()
        super().raise_()
        super().activateWindow()

    def showEvent(self, event) -> None:
        """Final, system-level guard: this fires for EVERY visibility
        transition — including those triggered by Qt's reopen handler
        and AppKit's `applicationShouldHandleReopen:` — even when the
        Python show() override is bypassed via the native C++ code path.
        If we weren't authorized, hide on the next event-loop tick."""
        if not self._show_authorized:
            log.warning("MainWindow.showEvent fired without authorization — hiding")
            QTimer.singleShot(0, super().hide)
            event.ignore()
            return
        super().showEvent(event)

    def closeEvent(self, event) -> None:
        event.ignore()
        self._show_authorized = False
        if hasattr(self, "_user_opened_flag"):
            self._user_opened_flag["flag"] = False
        super().hide()
