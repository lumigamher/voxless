"""Floating toast notifications anchored to the bottom-right of a window."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

ToastVariant = Literal["success", "error", "info"]

VARIANT_COLORS = {
    "success": ("#0a7c0a", "#dcfce7", "✓"),
    "error":   ("#b40000", "#fee2e2", "⚠"),
    "info":    ("#1d4ed8", "#dbeafe", "ⓘ"),
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

        accent, bg, glyph = VARIANT_COLORS.get(variant, VARIANT_COLORS["info"])
        self.setStyleSheet(
            f"""
            QFrame#ToastBody {{
              background: rgba(28,28,30,0.96);
              border-radius: 12px;
              padding: 0;
            }}
            QLabel#ToastIcon {{
              color: {accent};
              background: {bg};
              border-radius: 12px;
              font-size: 14px;
              font-weight: 700;
              min-width: 24px; min-height: 24px;
              max-width: 24px; max-height: 24px;
              qproperty-alignment: AlignCenter;
            }}
            QLabel#ToastText {{
              color: #f5f5f7;
              font-size: 13px;
              font-weight: 500;
            }}
            """
        )

        from PySide6.QtWidgets import QFrame

        body = QFrame(self)
        body.setObjectName("ToastBody")
        layout = QHBoxLayout(body)
        layout.setContentsMargins(12, 10, 16, 10)
        layout.setSpacing(10)

        icon = QLabel(glyph)
        icon.setObjectName("ToastIcon")
        layout.addWidget(icon)

        msg = QLabel(text)
        msg.setObjectName("ToastText")
        msg.setMaximumWidth(420)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(body)

        shadow = QGraphicsDropShadowEffect(body)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 110))
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
