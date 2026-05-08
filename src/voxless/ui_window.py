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
from PySide6.QtGui import QColor, QFont, QPainter, QPen
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
from .prompts import load_prompt

log = logging.getLogger(__name__)

QSS = """
QMainWindow, #Root { background: #f5f5f7; }
#Sidebar {
  background: #ececec;
  border-right: 1px solid #d8d8d8;
}
#SidebarTitle {
  color: #6e6e73;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  padding: 18px 16px 6px 16px;
  text-transform: uppercase;
}
QListWidget#NavList {
  background: transparent;
  border: none;
  outline: 0;
}
QListWidget#NavList::item {
  padding: 8px 16px;
  border-radius: 6px;
  margin: 2px 8px;
  color: #1d1d1f;
}
QListWidget#NavList::item:selected {
  background: rgba(0, 122, 255, 0.18);
  color: #1d1d1f;
}
QListWidget#NavList::item:hover { background: rgba(0,0,0,0.05); }

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
    ("home", "Inicio"),
    ("whisper", "Whisper"),
    ("ollama", "Ollama"),
    ("prompt", "Prompt"),
    ("history", "Historial"),
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
        for _key, label in NAV_ITEMS:
            self.nav.addItem(QListWidgetItem(label))
        self.nav.setCurrentRow(0)
        side_layout.addWidget(self.nav, 1)

        root_layout.addWidget(sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.home_page = HomePage()
        self.whisper_page = WhisperPage(cfg, self._handle_config_save)
        self.ollama_page = OllamaPage(cfg, self._handle_config_save)
        self.prompt_page = PromptPage(self._handle_prompt_save)
        self.history_page = HistoryPage()
        for w in (
            self.home_page,
            self.whisper_page,
            self.ollama_page,
            self.prompt_page,
            self.history_page,
        ):
            self.stack.addWidget(w)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        content_layout.addWidget(self.stack, 1)

        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)

        self._apply_qss()

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
