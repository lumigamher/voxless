"""Floating recording indicator — frameless, always-on-top pill anchored to
the bottom-center of the primary screen.

Shows live state: REC dot pulses + mini waveform during recording, "WRITING"
during processing. Hides on idle (with a soft fade-out).
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QPoint,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

ACCENT = "#dc2626"
AMBER  = "#c2410c"

STATE_LABEL = {
    "idle": "READY",
    "recording": "REC",
    "processing": "WRITING",
    "error": "ERROR",
}

STATE_DOT = {
    "idle": "#10b981",
    "recording": ACCENT,
    "processing": AMBER,
    "error": ACCENT,
}


class _MiniDot(QWidget):
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
        if self._pulse >= 1.0:
            self._pulse = 1.0; self._dir = -1.0
        elif self._pulse <= 0.0:
            self._pulse = 0.0; self._dir = 1.0
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._timer.isActive():
            halo = QColor(self._color); halo.setAlphaF(0.30 * self._pulse)
            p.setBrush(halo); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(self.rect())
        p.setBrush(self._color); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.rect().adjusted(2, 2, -2, -2))


class _MiniBars(QWidget):
    """7-bar mini meter."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(70, 22)
        self._levels = [0.0] * 7
        self._active = False

    def push(self, peak: float) -> None:
        self._levels = self._levels[1:] + [min(1.0, peak * 6.5)]
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._levels = [0.0] * 7
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        n = len(self._levels)
        bar_w = 6
        gap = 4
        total = n * (bar_w + gap) - gap
        x = (w - total) // 2
        cy = h / 2
        for level in self._levels:
            color = QColor(ACCENT) if self._active else QColor("#525252")
            if level > 0.85:
                color = QColor("#f87171")
            bh = max(3, int(level * (h - 6)))
            p.setBrush(color); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, int(cy - bh / 2), bar_w, bh, 1, 1)
            x += bar_w + gap


class RecorderOverlay(QWidget):
    """Floating pill that shows recording / processing state."""

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
        body.setStyleSheet("""
            #OverlayBody {
                background: rgba(15, 12, 10, 0.92);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 22px;
            }
            QLabel#OverlayState {
                color: #fafafa;
                font-family: "SF Mono", "Menlo", "Cascadia Mono", "Consolas", monospace;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.18em;
            }
            QLabel#OverlayHint {
                color: rgba(244, 240, 230, 0.55);
                font-family: "SF Mono", "Menlo", "Cascadia Mono", "Consolas", monospace;
                font-size: 9px;
                font-weight: 500;
                letter-spacing: 0.10em;
            }
        """)
        l = QHBoxLayout(body)
        l.setContentsMargins(16, 10, 18, 10)
        l.setSpacing(12)

        self._dot = _MiniDot()
        l.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        self._state_lbl = QLabel("READY")
        self._state_lbl.setObjectName("OverlayState")
        text_col.addWidget(self._state_lbl)
        self._hint_lbl = QLabel("voxless")
        self._hint_lbl.setObjectName("OverlayHint")
        text_col.addWidget(self._hint_lbl)
        l.addLayout(text_col)

        self._bars = _MiniBars()
        l.addWidget(self._bars, 0, Qt.AlignmentFlag.AlignVCenter)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(body)
        self.adjustSize()

        self._fade: QPropertyAnimation | None = None
        self._state = "idle"

    # ── public API ──────────────────────────────────────────
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

    # ── animation helpers ───────────────────────────────────
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
