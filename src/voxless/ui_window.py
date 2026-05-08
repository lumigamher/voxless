"""Main application window — sidebar + pages, live waveform, history.

Designed to feel native on macOS (Qt picks up the system style automatically)
and styled with QSS to feel macOS-like on Windows.
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
from .permissions import Permission, list_permissions
from .prompts import load_prompt

log = logging.getLogger(__name__)

QSS = """
* { font-family: -apple-system, "SF Pro Text", "SF Pro Display", "Segoe UI", system-ui, sans-serif; }
QMainWindow, #Root { background: #f5f5f7; }
#Sidebar {
  background: rgba(236, 236, 236, 0.96);
  border-right: 1px solid #d8d8d8;
}
#SidebarTitle {
  color: #6e6e73;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 22px 18px 8px 18px;
  text-transform: uppercase;
}
QListWidget#NavList {
  background: transparent;
  border: none;
  outline: 0;
  font-size: 13px;
}
QListWidget#NavList::item {
  padding: 8px 14px;
  border-radius: 8px;
  margin: 2px 10px;
  color: #1d1d1f;
}
QListWidget#NavList::item:selected {
  background: rgba(0, 122, 255, 0.16);
  color: #1d1d1f;
}
QListWidget#NavList::item:hover:!selected { background: rgba(0,0,0,0.05); }

#StatusBanner {
  background: #ffffff;
  border: 1px solid #e5e5ea;
  border-radius: 14px;
  padding: 14px 18px;
}
#StatusDot { qproperty-alignment: AlignCenter; }
#StatusText { font-size: 14px; color: #1d1d1f; font-weight: 500; }
#StatusSub  { font-size: 12px; color: #8e8e93; }

QLabel#PageTitle { font-size: 22px; font-weight: 700; color: #1d1d1f; }
QLabel#PageSub   { font-size: 13px; color: #6e6e73; }
QLabel.Section   { font-size: 12px; font-weight: 600; color: #6e6e73;
                   letter-spacing: 0.05em; text-transform: uppercase; }

#Card {
  background: #ffffff;
  border: 1px solid #e5e5ea;
  border-radius: 12px;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
  background: #ffffff;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  padding: 6px 10px;
  selection-background-color: #007aff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus { border-color: #007aff; }
QComboBox::drop-down { border: 0; width: 18px; }

QPushButton {
  background: #ffffff;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  padding: 6px 14px;
  color: #1d1d1f;
}
QPushButton:hover { background: #f0f0f3; }
QPushButton#Primary {
  background: #007aff; color: white; border-color: #006fe6; font-weight: 600;
}
QPushButton#Primary:hover { background: #0a84ff; }
QPushButton#Danger { color: #b40000; }

QListWidget#History {
  background: transparent; border: none; outline: 0;
}
QListWidget#History::item {
  background: #ffffff;
  border: 1px solid #e5e5ea;
  border-radius: 10px;
  margin: 4px 0;
  padding: 10px 12px;
  color: #1d1d1f;
}
QListWidget#History::item:hover { background: #fafafa; }
QListWidget#History::item:selected {
  border-color: #007aff;
  background: rgba(0, 122, 255, 0.08);
}

QCheckBox { color: #1d1d1f; }
QCheckBox::indicator {
  width: 18px; height: 18px;
  border: 1px solid #c7c7cc; border-radius: 4px; background: white;
}
QCheckBox::indicator:checked { background: #007aff; border-color: #007aff; }
"""

QSS_DARK_OVERRIDES = """
QMainWindow, #Root { background: #1c1c1e; }
#Sidebar { background: #2c2c2e; border-right-color: #3a3a3c; }
#SidebarTitle { color: #8e8e93; }
QListWidget#NavList::item { color: #f5f5f7; }
QListWidget#NavList::item:hover { background: rgba(255,255,255,0.06); }
#StatusBanner { background: #2c2c2e; border-color: #3a3a3c; }
#StatusText { color: #f5f5f7; }
#Card { background: #2c2c2e; border-color: #3a3a3c; }
QLabel#PageTitle { color: #f5f5f7; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
  background: #1c1c1e; border-color: #3a3a3c; color: #f5f5f7;
}
QPushButton { background: #2c2c2e; color: #f5f5f7; border-color: #3a3a3c; }
QPushButton:hover { background: #3a3a3c; }
QListWidget#History::item { background: #2c2c2e; border-color: #3a3a3c; color: #f5f5f7; }
QListWidget#History::item:hover { background: #36363a; }
QCheckBox { color: #f5f5f7; }
QCheckBox::indicator { background: #1c1c1e; border-color: #3a3a3c; }
"""

NAV_ITEMS = [
    ("home",        "Inicio",     "◉"),
    ("general",     "General",    "⚙"),
    ("permissions", "Permisos",   "🔒"),
    ("whisper",     "Whisper",    "✎"),
    ("ollama",      "Ollama",     "◯"),
    ("prompt",      "Prompt",     "❝"),
    ("history",     "Historial",  "⏱"),
]

STATE_TEXT = {
    "idle": ("Listo", "Mantén la tecla configurada para grabar"),
    "recording": ("Grabando", "Habla — al soltar la tecla se transcribe"),
    "processing": ("Procesando", "Whisper + Ollama trabajando"),
    "error": ("Error", "Revisa los logs para detalles"),
}

STATE_DOT_COLOR = {
    "idle": "#34c759",
    "recording": "#ff3b30",
    "processing": "#ff9500",
    "error": "#ff3b30",
}


class StatusDot(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._color = QColor(STATE_DOT_COLOR["idle"])
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._direction = 1.0

    def set_state(self, state: str) -> None:
        self._color = QColor(STATE_DOT_COLOR.get(state, STATE_DOT_COLOR["idle"]))
        if state in ("recording", "processing"):
            self._timer.start(33)
        else:
            self._timer.stop()
            self._pulse = 0.0
        self.update()

    def _tick(self) -> None:
        self._pulse += 0.08 * self._direction
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
            halo.setAlphaF(0.35 * self._pulse)
            p.setBrush(halo)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(self.rect())
        p.setBrush(self._color)
        p.setPen(Qt.PenStyle.NoPen)
        inner = self.rect().adjusted(2, 2, -2, -2)
        p.drawEllipse(inner)


class WaveformView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._levels: list[float] = [0.0] * 80
        self._active = False

    def push(self, peak: float) -> None:
        self._levels.append(min(1.0, peak * 6.0))
        if len(self._levels) > 80:
            self._levels = self._levels[-80:]
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._levels = [0.0] * 80
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        bar_w = max(2, w // len(self._levels) - 2)
        gap = 2
        total = len(self._levels) * (bar_w + gap)
        x = (w - total) // 2
        center_y = h / 2
        color = QColor("#ff3b30" if self._active else "#c7c7cc")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        for level in self._levels:
            bar_h = max(3, int(level * (h - 8)))
            p.drawRoundedRect(x, int(center_y - bar_h / 2), bar_w, bar_h, 2, 2)
            x += bar_w + gap


def _card(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("Card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    if title:
        lbl = QLabel(title)
        lbl.setProperty("class", "Section")
        lbl.setStyleSheet("color:#6e6e73; font-size:12px; font-weight:600; letter-spacing:0.05em; text-transform:uppercase;")
        layout.addWidget(lbl)
    return card, layout


def _row(label: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    lbl = QLabel(label)
    lbl.setMinimumWidth(140)
    lbl.setStyleSheet("color:#1d1d1f;")
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    return row


class HomePage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("voxless")
        title.setObjectName("PageTitle")
        sub = QLabel("Dictado push-to-talk local con Whisper + Ollama")
        sub.setObjectName("PageSub")
        layout.addWidget(title)
        layout.addWidget(sub)

        banner = QFrame()
        banner.setObjectName("StatusBanner")
        b_layout = QHBoxLayout(banner)
        b_layout.setSpacing(14)

        self.dot = StatusDot()
        b_layout.addWidget(self.dot)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.status_text = QLabel(STATE_TEXT["idle"][0])
        self.status_text.setObjectName("StatusText")
        self.status_sub = QLabel(STATE_TEXT["idle"][1])
        self.status_sub.setObjectName("StatusSub")
        text_col.addWidget(self.status_text)
        text_col.addWidget(self.status_sub)
        b_layout.addLayout(text_col, 1)

        self.waveform = WaveformView()
        self.waveform.setMinimumWidth(220)
        b_layout.addWidget(self.waveform, 2)

        layout.addWidget(banner)

        last_card, last_layout = _card("Última transcripción")
        self.last_text = QLabel("—")
        self.last_text.setWordWrap(True)
        self.last_text.setStyleSheet("color:#1d1d1f; font-size:14px;")
        self.last_text.setMinimumHeight(60)
        last_layout.addWidget(self.last_text)
        layout.addWidget(last_card)

        layout.addStretch(1)

    def set_state(self, state: str) -> None:
        text, sub = STATE_TEXT.get(state, STATE_TEXT["idle"])
        self.status_text.setText(text)
        self.status_sub.setText(sub)
        self.dot.set_state(state)
        self.waveform.set_active(state == "recording")


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

    if event.text() and event.text().strip() and len(event.text()) == 1:
        ch = event.text().lower()
        if ch.isalnum():
            return ch

    return None


def _spec_pretty(spec: str) -> str:
    if not spec:
        return "(sin asignar)"
    parts = [p.strip("<> ") for p in spec.split("+")]
    label_map = {
        "right_option": "⌥ Right",
        "left_option": "⌥ Left",
        "alt": "⌥",
        "cmd": "⌘",
        "cmd_l": "⌘ Left",
        "cmd_r": "⌘ Right",
        "ctrl": "⌃",
        "ctrl_l": "⌃ Left",
        "ctrl_r": "⌃ Right",
        "shift": "⇧",
        "shift_l": "⇧ Left",
        "shift_r": "⇧ Right",
        "space": "Space",
        "tab": "Tab",
        "esc": "Esc",
        "caps_lock": "Caps Lock",
        "fn": "Fn",
    }
    pretty = []
    for p in parts:
        if p in label_map:
            pretty.append(label_map[p])
        elif p.startswith("f") and p[1:].isdigit():
            pretty.append(p.upper())
        else:
            pretty.append(p.upper())
    return " + ".join(pretty)


class HotkeyRecorder(QPushButton):
    captured = Signal(str)  # emits pynput-compatible spec

    def __init__(self, current: str = "") -> None:
        super().__init__()
        self._spec = current
        self._recording = False
        self.setMinimumHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._toggle_record)
        self._update_text()

    def spec(self) -> str:
        return self._spec

    def set_spec(self, spec: str) -> None:
        self._spec = spec
        self._recording = False
        self._update_text()

    def _toggle_record(self) -> None:
        self._recording = not self._recording
        if self._recording:
            self.setFocus(Qt.FocusReason.OtherFocusReason)
            self.grabKeyboard()
        else:
            self.releaseKeyboard()
        self._update_text()

    def _update_text(self) -> None:
        if self._recording:
            self.setText("Presiona una tecla…   (Esc para cancelar)")
            self.setStyleSheet(
                "QPushButton { background:#fff7d6; border:1px solid #f0aa1e;"
                " border-radius:8px; padding:8px 14px; font-weight:600; }"
            )
        else:
            self.setText(_spec_pretty(self._spec))
            self.setStyleSheet("")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._recording:
            return super().keyPressEvent(event)

        if event.key() == Qt.Key.Key_Escape and not (
            event.modifiers() & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ControlModifier
                                 | Qt.KeyboardModifier.MetaModifier | Qt.KeyboardModifier.ShiftModifier)
        ):
            self._recording = False
            self.releaseKeyboard()
            self._update_text()
            return

        name = _named_key_from_event(event)
        if not name:
            return

        mods: list[str] = []
        m = event.modifiers()
        if m & Qt.KeyboardModifier.ControlModifier and name not in ("ctrl", "ctrl_l", "ctrl_r"):
            mods.append("ctrl")
        if m & Qt.KeyboardModifier.AltModifier and name not in ("alt", "left_option", "right_option"):
            mods.append("alt")
        if m & Qt.KeyboardModifier.MetaModifier and name not in ("cmd", "cmd_l", "cmd_r"):
            mods.append("cmd")
        if m & Qt.KeyboardModifier.ShiftModifier and name not in ("shift", "shift_l", "shift_r"):
            mods.append("shift")

        if mods:
            spec = "+".join(f"<{x}>" for x in mods) + "+" + name
        else:
            spec = name

        self._spec = spec
        self._recording = False
        self.releaseKeyboard()
        self._update_text()
        self.captured.emit(spec)


class GeneralPage(QWidget):
    def __init__(self, cfg: Config, on_save: Callable[[Config], None]) -> None:
        super().__init__()
        self._cfg = cfg
        self._on_save = on_save
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(_title_block(
            "General",
            "Hotkey, modo de activación y duración mínima.",
        ))

        card, c = _card("Hotkey")
        self.hotkey_recorder = HotkeyRecorder(cfg.hotkey)
        c.addLayout(_row("Tecla", self.hotkey_recorder))
        hint = QLabel("Click en el botón y presiona la tecla (o combinación) que quieras usar.")
        hint.setStyleSheet("color:#6e6e73; font-size:12px; padding-left:152px;")
        c.addWidget(hint)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Mantener presionado (push-to-talk)", "hold")
        self.mode_combo.addItem("Tap: tocar para iniciar / tocar para terminar", "toggle")
        idx = self.mode_combo.findData(cfg.hotkey_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        c.addLayout(_row("Modo", self.mode_combo))

        layout.addWidget(card)

        card2, c2 = _card("Comportamiento")
        self.min_ms = QSpinBox()
        self.min_ms.setRange(0, 5000)
        self.min_ms.setSingleStep(50)
        self.min_ms.setSuffix(" ms")
        self.min_ms.setValue(cfg.min_record_ms)
        c2.addLayout(_row("Duración mínima", self.min_ms))

        self.sound = QCheckBox("Sonido al iniciar / detener grabación")
        self.sound.setChecked(cfg.sound_feedback)
        c2.addWidget(self.sound)

        layout.addWidget(card2)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_btn = QPushButton("Guardar")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)
        layout.addStretch(1)

    def _save(self) -> None:
        self._cfg.hotkey = self.hotkey_recorder.spec().strip() or "right_option"
        self._cfg.hotkey_mode = self.mode_combo.currentData()
        self._cfg.min_record_ms = int(self.min_ms.value())
        self._cfg.sound_feedback = self.sound.isChecked()
        self._on_save(self._cfg)


class PermissionsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._rows: list[tuple[Permission, QLabel]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(_title_block(
            "Permisos",
            "Necesarios para que voxless escuche tu hotkey y grabe el micrófono globalmente.",
        ))

        card, c = _card("Estado")
        perms = list_permissions()
        if not perms:
            note = QLabel("Tu plataforma no requiere configuración adicional.")
            note.setStyleSheet("color:#6e6e73;")
            c.addWidget(note)
        else:
            for perm in perms:
                c.addWidget(self._build_row(perm))

        refresh = QPushButton("Verificar de nuevo")
        refresh.clicked.connect(self.refresh)
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(refresh)
        c.addLayout(actions)
        layout.addWidget(card)

        tips_card, tc = _card("Consejos")
        tips = QLabel(
            "• En macOS, si el panel de System Settings no deja seleccionar voxless, arrastra "
            "<code>/Applications/voxless.app</code> desde Finder al panel.\n"
            "• Tras conceder un permiso, vuelve aquí y pulsa <b>Verificar de nuevo</b>.\n"
            "• Si cambias o reemplazas voxless.app, macOS puede pedirte re-autorizar."
        )
        tips.setWordWrap(True)
        tips.setTextFormat(Qt.TextFormat.RichText)
        tips.setStyleSheet("color:#1d1d1f; font-size:13px;")
        tc.addWidget(tips)
        layout.addWidget(tips_card)

        layout.addStretch(1)

    def _build_row(self, perm: Permission) -> QWidget:
        row = QFrame()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 8, 0, 8)
        rl.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t = QLabel(perm.title)
        t.setStyleSheet("color:#1d1d1f; font-weight:600; font-size:14px;")
        d = QLabel(perm.description)
        d.setStyleSheet("color:#6e6e73; font-size:12px;")
        d.setWordWrap(True)
        title_col.addWidget(t)
        title_col.addWidget(d)
        rl.addLayout(title_col, 1)

        status = QLabel("…")
        status.setMinimumWidth(96)
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(status)

        if perm.request is not None:
            req_btn = QPushButton(perm.request_label)
            req_btn.setObjectName("Primary")
            req_btn.clicked.connect(self._make_request_handler(perm))
            rl.addWidget(req_btn)

        btn = QPushButton("Abrir ajustes")
        btn.clicked.connect(perm.open_settings)
        rl.addWidget(btn)

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
                "color:#0a7c0a; background:rgba(52,199,89,0.15);"
                "border-radius:8px; padding:4px 10px; font-weight:600;"
            )
        elif st == "denied":
            label.setText("Falta")
            label.setStyleSheet(
                "color:#b40000; background:rgba(255,59,48,0.15);"
                "border-radius:8px; padding:4px 10px; font-weight:600;"
            )
        else:
            label.setText("Desconocido")
            label.setStyleSheet(
                "color:#6e6e73; background:rgba(142,142,147,0.15);"
                "border-radius:8px; padding:4px 10px; font-weight:600;"
            )

    def refresh(self) -> None:
        for perm, lbl in self._rows:
            self._render(perm, lbl)


class WhisperPage(QWidget):
    def __init__(self, cfg: Config, on_save: Callable[[Config], None]) -> None:
        super().__init__()
        self._cfg = cfg
        self._on_save = on_save
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(_title_block("Whisper", "Modelo local de transcripción (faster-whisper)"))

        card, c = _card("Modelo")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText(cfg.whisper.model)
        c.addLayout(_row("Modelo", self.model_combo))

        self.lang_edit = QLineEdit(cfg.whisper.language or "")
        self.lang_edit.setPlaceholderText("auto (vacío) o ej. es, en, fr")
        c.addLayout(_row("Idioma", self.lang_edit))

        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["int8", "int8_float16", "float16", "float32"])
        self.compute_combo.setCurrentText(cfg.whisper.compute_type)
        c.addLayout(_row("Compute type", self.compute_combo))

        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cpu"])
        self.device_combo.setCurrentText(cfg.whisper.device)
        c.addLayout(_row("Device", self.device_combo))

        layout.addWidget(card)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_btn = QPushButton("Guardar")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)
        layout.addStretch(1)

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(_title_block("Ollama", "Modelo local de limpieza de texto"))

        card, c = _card("Conexión")
        self.enabled = QCheckBox("Habilitar limpieza con Ollama")
        self.enabled.setChecked(cfg.ollama.enabled)
        c.addWidget(self.enabled)

        self.url = QLineEdit(cfg.ollama.url)
        c.addLayout(_row("URL", self.url))

        self.model = QLineEdit(cfg.ollama.model)
        self.model.setPlaceholderText("ej. gemma3:1b, llama3.2:3b, qwen2.5:3b")
        c.addLayout(_row("Modelo", self.model))

        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(1.0, 600.0)
        self.timeout.setDecimals(1)
        self.timeout.setSuffix(" s")
        self.timeout.setValue(cfg.ollama.timeout_s)
        c.addLayout(_row("Timeout", self.timeout))

        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setDecimals(2)
        self.temperature.setValue(cfg.ollama.temperature)
        c.addLayout(_row("Temperatura", self.temperature))

        layout.addWidget(card)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_btn = QPushButton("Guardar")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)
        layout.addStretch(1)

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(_title_block(
            "Prompt",
            "Plantilla que recibe Ollama. Úsala para reglas de estilo y few-shot.",
        ))

        self.editor = QPlainTextEdit()
        self.editor.setPlainText(load_prompt())
        font = QFont("Menlo")
        if not font.exactMatch():
            font = QFont("Consolas")
        font.setPointSize(11)
        self.editor.setFont(font)
        self.editor.setMinimumHeight(360)
        layout.addWidget(self.editor, 1)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_btn = QPushButton("Guardar prompt")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(lambda: self._on_save(self.editor.toPlainText()))
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)


class HistoryPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(_title_block(
            "Historial",
            "Últimas transcripciones de esta sesión (máx. 100).",
        ))

        self.list = QListWidget()
        self.list.setObjectName("History")
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.list, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        copy_btn = QPushButton("Copiar")
        copy_btn.clicked.connect(self._copy_selected)
        clear_btn = QPushButton("Limpiar")
        clear_btn.setObjectName("Danger")
        clear_btn.clicked.connect(lambda: self.list.clear())
        actions.addWidget(copy_btn)
        actions.addWidget(clear_btn)
        layout.addLayout(actions)

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

    def _copy_selected(self) -> None:
        from PySide6.QtWidgets import QApplication
        item = self.list.currentItem()
        if not item:
            return
        text = item.data(Qt.ItemDataRole.UserRole) or item.text()
        QApplication.clipboard().setText(text)


def _title_block(title: str, subtitle: str) -> QWidget:
    w = QWidget()
    l = QVBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    s = QLabel(subtitle)
    s.setObjectName("PageSub")
    l.addWidget(t)
    l.addWidget(s)
    return w


class MainWindow(QMainWindow):
    config_changed = Signal(object)
    prompt_changed = Signal(str)
    quit_requested = Signal()

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.setWindowTitle("voxless")
        self.setMinimumSize(QSize(880, 580))
        self._cfg = cfg

        root = QWidget()
        root.setObjectName("Root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(180)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 12)
        side_layout.setSpacing(0)

        title = QLabel("voxless")
        title.setObjectName("SidebarTitle")
        side_layout.addWidget(title)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        for _key, label, icon in NAV_ITEMS:
            self.nav.addItem(QListWidgetItem(f"  {icon}    {label}"))
        self.nav.setCurrentRow(0)
        side_layout.addWidget(self.nav, 1)

        version_lbl = QLabel("voxless · 0.1.3")
        version_lbl.setStyleSheet("color:#a1a1a6; font-size:10px; padding:8px 18px 12px 18px;")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        side_layout.addWidget(version_lbl)

        root_layout.addWidget(sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.home_page = HomePage()
        self.general_page = GeneralPage(cfg, self._handle_config_save)
        self.permissions_page = PermissionsPage()
        self.whisper_page = WhisperPage(cfg, self._handle_config_save)
        self.ollama_page = OllamaPage(cfg, self._handle_config_save)
        self.prompt_page = PromptPage(self._handle_prompt_save)
        self.history_page = HistoryPage()
        for w in (
            self.home_page,
            self.general_page,
            self.permissions_page,
            self.whisper_page,
            self.ollama_page,
            self.prompt_page,
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
            qss = QSS + QSS_DARK_OVERRIDES
        self.setStyleSheet(qss)

    def _handle_config_save(self, cfg: Config) -> None:
        try:
            save_config(cfg)
        except Exception:
            log.exception("Failed to save config")
            return
        self.config_changed.emit(cfg)

    def _handle_prompt_save(self, text: str) -> None:
        try:
            save_prompt(text)
        except Exception:
            log.exception("Failed to save prompt")
            return
        self.prompt_changed.emit(text)

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
