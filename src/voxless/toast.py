"""Floating toast — Nothing-style square LED slip with red stripe."""

from __future__ import annotations

from typing import Literal

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

ToastVariant = Literal["success", "error", "info"]

VARIANTS = {
    "success": ("#5fdb5f", "OK"),
    "error":   ("#ff3636", "ERR"),
    "info":    ("#ffaa00", "INFO"),
}


class Toast(QWidget):
    def __init__(
        self,
        text: str,
        variant: ToastVariant = "success",
        parent: QWidget | None = None,
        duration_ms: int = 2400,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        stripe, label = VARIANTS.get(variant, VARIANTS["info"])
        self.setStyleSheet(
            f"""
            QFrame#ToastBody {{
              background: #000000;
              border: 1px solid #2a2a2a;
              border-radius: 2px;
            }}
            QLabel#ToastStripe {{
              background: {stripe};
              max-width: 4px;
              min-width: 4px;
              border-radius: 0;
            }}
            QLabel#ToastLabel {{
              color: {stripe};
              font-family: "SF Mono", "Menlo", "JetBrains Mono", monospace;
              font-size: 10px;
              font-weight: 800;
              letter-spacing: 0.22em;
            }}
            QLabel#ToastText {{
              color: #ffffff;
              font-family: "SF Mono", "Menlo", "JetBrains Mono", monospace;
              font-size: 11px;
              font-weight: 700;
              letter-spacing: 0.08em;
              text-transform: uppercase;
            }}
            """
        )

        body = QFrame(self)
        body.setObjectName("ToastBody")
        body_l = QHBoxLayout(body)
        body_l.setContentsMargins(0, 0, 0, 0)
        body_l.setSpacing(0)

        stripe_w = QLabel("")
        stripe_w.setObjectName("ToastStripe")
        stripe_w.setFixedWidth(4)
        body_l.addWidget(stripe_w)

        inner = QHBoxLayout()
        inner.setContentsMargins(18, 14, 22, 14)
        inner.setSpacing(16)
        lbl = QLabel(label)
        lbl.setObjectName("ToastLabel")
        inner.addWidget(lbl)
        msg = QLabel(text)
        msg.setObjectName("ToastText")
        msg.setMaximumWidth(420)
        msg.setWordWrap(True)
        inner.addWidget(msg)

        wrap = QFrame()
        wrap_l = QVBoxLayout(wrap)
        wrap_l.setContentsMargins(0, 0, 0, 0)
        wrap_l.addLayout(inner)
        body_l.addWidget(wrap, 1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(body)

        shadow = QGraphicsDropShadowEffect(body)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 130))
        body.setGraphicsEffect(shadow)

        self.adjustSize()
        self._duration_ms = duration_ms

    def show_for(self, parent_window: QWidget) -> None:
        self.setParent(parent_window)
        self.adjustSize()
        margin = 24
        x = parent_window.width() - self.width() - margin
        y = parent_window.height() - self.height() - margin
        self._target_pos = QPoint(x, y)
        self.move(QPoint(x, y + 16))
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        self._fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_in.setDuration(160)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._slide_in = QPropertyAnimation(self, b"pos", self)
        self._slide_in.setDuration(220)
        self._slide_in.setStartValue(self.pos())
        self._slide_in.setEndValue(self._target_pos)
        self._slide_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_in.start()
        self._slide_in.start()

        QTimer.singleShot(self._duration_ms, self._dismiss)

    def _dismiss(self) -> None:
        self._fade_out = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_out.setDuration(180)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.finished.connect(self.deleteLater)
        self._fade_out.start()
