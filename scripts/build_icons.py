"""Render assets/voxless.svg into a macOS .icns and a Windows .ico.

Run from the repo root: ``python scripts/build_icons.py``.
Requires PySide6 (already a runtime dep).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG = ASSETS / "voxless.svg"
ICONSET_DIR = ASSETS / "voxless.iconset"
ICNS_PATH = ASSETS / "voxless.icns"
ICO_PATH = ASSETS / "voxless.ico"


def _render_svg(size: int):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    svg = QSvgRenderer(str(SVG))
    if not svg.isValid():
        raise SystemExit(f"SVG invalid: {SVG}")
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    svg.render(p)
    p.end()
    return img


def build_icns() -> None:
    if sys.platform != "darwin":
        print("Skipping .icns (not macOS)")
        return
    if shutil.which("iconutil") is None:
        print("Skipping .icns (iconutil not found)")
        return
    ICONSET_DIR.mkdir(exist_ok=True)
    pairs = [(16, 1), (16, 2), (32, 1), (32, 2), (128, 1), (128, 2),
             (256, 1), (256, 2), (512, 1), (512, 2)]
    for size, scale in pairs:
        img = _render_svg(size * scale)
        suffix = f"@{scale}x" if scale > 1 else ""
        img.save(str(ICONSET_DIR / f"icon_{size}x{size}{suffix}.png"), "PNG")
    subprocess.run(
        ["iconutil", "-c", "icns", str(ICONSET_DIR), "-o", str(ICNS_PATH)],
        check=True,
    )
    shutil.rmtree(ICONSET_DIR, ignore_errors=True)
    print(f"Wrote {ICNS_PATH}")


def build_ico() -> None:
    img = _render_svg(256)
    img.save(str(ICO_PATH), "ICO")
    print(f"Wrote {ICO_PATH}")


if __name__ == "__main__":
    if not SVG.exists():
        raise SystemExit(f"Missing SVG: {SVG}")
    build_icns()
    build_ico()
