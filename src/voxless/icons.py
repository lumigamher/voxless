"""Inline Lucide-style icons rendered through QSvgRenderer.

Embedding SVG strings keeps the wheel small (no asset bundling) and lets
us recolor every icon by interpolating ``{stroke}`` at render time.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ICONS = {
    "home": (
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M3 11.5L12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"'
        ' stroke="{stroke}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ),
    "settings": (
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<circle cx="12" cy="12" r="3" stroke="{stroke}" stroke-width="1.6"/>'
        '<path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.82 2.83l-.07-.07a1.7 1.7 0 0 0-1.86-.34 1.7 1.7 0 0 0-1.04 1.56V21a2 2 0 1 1-4 0v-.07a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06A2 2 0 1 1 4.13 16.9l.07-.07a1.7 1.7 0 0 0 .34-1.86 1.7 1.7 0 0 0-1.56-1.04H3a2 2 0 1 1 0-4h.07a1.7 1.7 0 0 0 1.56-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06A2 2 0 1 1 7.04 4.06l.07.07a1.7 1.7 0 0 0 1.86.34h.04A1.7 1.7 0 0 0 10 3.04V3a2 2 0 1 1 4 0v.07a1.7 1.7 0 0 0 1.04 1.56 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.82l-.07.07a1.7 1.7 0 0 0-.34 1.86V9a1.7 1.7 0 0 0 1.56 1.04H21a2 2 0 1 1 0 4h-.07a1.7 1.7 0 0 0-1.56 1.04z"'
        ' stroke="{stroke}" stroke-width="1.4" stroke-linejoin="round"/></svg>'
    ),
    "shield": (
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"'
        ' stroke="{stroke}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ),
    "mic": (
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="9" y="3" width="6" height="12" rx="3" stroke="{stroke}" stroke-width="1.6"/>'
        '<path d="M5 11a7 7 0 0 0 14 0M12 18v3" stroke="{stroke}" stroke-width="1.6" stroke-linecap="round"/></svg>'
    ),
    "spark": (
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M12 3v3m0 12v3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1M3 12h3m12 0h3M5.6 18.4l2.1-2.1m8.6-8.6 2.1-2.1"'
        ' stroke="{stroke}" stroke-width="1.6" stroke-linecap="round"/></svg>'
    ),
    "text": (
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M4 6h16M4 12h12M4 18h16" stroke="{stroke}" stroke-width="1.6" stroke-linecap="round"/></svg>'
    ),
    "clock": (
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<circle cx="12" cy="12" r="9" stroke="{stroke}" stroke-width="1.6"/>'
        '<path d="M12 7v5l3 2" stroke="{stroke}" stroke-width="1.6" stroke-linecap="round"/></svg>'
    ),
    "chevron-right": (
        '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="m9 6 6 6-6 6" stroke="{stroke}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ),
}


def render_icon(name: str, size: int = 18, color: str = "#1d1d1f") -> QIcon:
    svg = ICONS.get(name)
    if not svg:
        return QIcon()
    rendered = svg.replace("{stroke}", color)
    img = QImage(size * 2, size * 2, QImage.Format.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    QSvgRenderer(rendered.encode("utf-8")).render(painter)
    painter.end()
    pix = QPixmap.fromImage(img)
    pix.setDevicePixelRatio(2.0)
    return QIcon(pix)
