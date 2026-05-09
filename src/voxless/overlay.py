"""Floating Nothing-style glyph indicator — frameless, always-on-top pill
anchored to the bottom-center of the primary screen.

Pure black + white + Nothing red. Pixel LED meter, square dot, monospace.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QPoint,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QGuiApplication, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

ACCENT = "#ff3636"
INK    = "#ffffff"
BG     = "#000000"
DIM    = "#525252"

STATE_LABEL = {
    "idle": "READY",
    "recording": "REC",
    "processing": "WRITE",
    "error": "ERROR",
}

STATE_DOT = {
    "idle": "#5fdb5f",
    "recording": ACCENT,
    "processing": "#ffaa00",
    "error": ACCENT,
}


class _PixelDot(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(10, 10)
        self._color = QColor(STATE_DOT["idle"])
        self._pulse = 0.0
        self._dir = 1.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def set_state(self, state: str) -> None:
        self._color = QColor(STATE_DOT.get(state, STATE_DOT["idle"]))
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
        if self._timer.isActive():
            halo = QColor(self._color); halo.setAlphaF(0.30 * self._pulse)
            p.setBrush(halo); p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(self.rect())
        p.setBrush(self._color); p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect().adjusted(2, 2, -2, -2))


class _PixelMeter(QWidget):
    """Pixel-LED 5-row × 9-col meter."""

    COLS = 9
    ROWS = 5

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(74, 26)
        self._levels = [0.0] * self.COLS
        self._active = False

    def push(self, peak: float) -> None:
        self._levels = self._levels[1:] + [min(1.0, peak * 6.5)]
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._levels = [0.0] * self.COLS
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()
        cell_w = 6
        cell_h = 4
        gap = 1
        total_w = self.COLS * (cell_w + gap) - gap
        total_h = self.ROWS * (cell_h + gap) - gap
        x0 = (w - total_w) // 2
        y0 = (h - total_h) // 2

        for c, level in enumerate(self._levels):
            lit_rows = int(level * self.ROWS)
            for r in range(self.ROWS):
                cx = x0 + c * (cell_w + gap)
                cy = y0 + (self.ROWS - 1 - r) * (cell_h + gap)
                if r < lit_rows:
                    color = QColor(ACCENT) if (r >= self.ROWS - 1 and self._active) else QColor(INK)
                else:
                    color = QColor("#1f1f1f")
                p.setBrush(color); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(cx, cy, cell_w, cell_h)


class RecorderOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        body = QFrame(self)
        body.setObjectName("OverlayBody")
        body.setStyleSheet(f"""
            #OverlayBody {{
                background: {BG};
                border: 1px solid #2a2a2a;
                border-radius: 2px;
            }}
            QLabel#OverlayState {{
                color: {INK};
                font-family: "SF Mono", "Menlo", "Cascadia Mono", "Consolas", monospace;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.22em;
            }}
            QLabel#OverlayHint {{
                color: {DIM};
                font-family: "SF Mono", "Menlo", "Cascadia Mono", "Consolas", monospace;
                font-size: 9px;
                font-weight: 600;
                letter-spacing: 0.18em;
            }}
        """)
        l = QHBoxLayout(body)
        l.setContentsMargins(18, 12, 22, 12)
        l.setSpacing(14)

        self._dot = _PixelDot()
        l.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._state_lbl = QLabel("READY")
        self._state_lbl.setObjectName("OverlayState")
        text_col.addWidget(self._state_lbl)
        self._hint_lbl = QLabel("VOXLESS")
        self._hint_lbl.setObjectName("OverlayHint")
        text_col.addWidget(self._hint_lbl)
        l.addLayout(text_col)

        self._bars = _PixelMeter()
        l.addWidget(self._bars, 0, Qt.AlignmentFlag.AlignVCenter)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(body)
        self.adjustSize()

        self._fade: QPropertyAnimation | None = None
        self._state = "idle"

    def set_state(self, state: str) -> None:
        self._state = state
        self._state_lbl.setText(STATE_LABEL.get(state, state.upper()))
        self._dot.set_state(state)
        self._bars.set_active(state == "recording")
        if state == "idle":
            self._fade_out()
        else:
            self._fade_in()

    def push_peak(self, peak: float) -> None:
        if self._state == "recording":
            self._bars.push(peak)

    def _anchor_position(self) -> QPoint:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return QPoint(40, 40)
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + geo.height() - self.height() - 56
        return QPoint(x, y)

    def _fade_in(self) -> None:
        self.adjustSize()
        target = self._anchor_position()
        if not self.isVisible():
            self.move(target.x(), target.y() + 12)
            self.setWindowOpacity(0.0)
            self.show()
            self.raise_()
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(180)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.start()

        slide = QPropertyAnimation(self, b"pos", self)
        slide.setDuration(220)
        slide.setStartValue(self.pos())
        slide.setEndValue(target)
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide.start()
        self._slide = slide

    def _fade_out(self) -> None:
        if not self.isVisible():
            return
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(220)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self.hide)
        self._fade.start()
