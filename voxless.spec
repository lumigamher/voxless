# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for voxless.

Builds a single-folder app bundle. Used by both the macOS and Windows
release workflows in .github/workflows/release.yml.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None
ROOT = Path(SPECPATH).resolve()

datas = []
datas += [(str(ROOT / "src" / "voxless" / "_data" / "default_prompt.md"), "voxless/_data")]
datas += collect_data_files("faster_whisper")
datas += collect_data_files("ctranslate2")

binaries = []
binaries += collect_dynamic_libs("ctranslate2")
binaries += collect_dynamic_libs("av")
binaries += collect_dynamic_libs("onnxruntime")
binaries += collect_dynamic_libs("sounddevice")
binaries += collect_dynamic_libs("soundfile")

hiddenimports = [
    "voxless",
    "voxless.app",
    "voxless.config",
    "voxless.hotkey",
    "voxless.llm",
    "voxless.logging_setup",
    "voxless.paster",
    "voxless.prompts",
    "voxless.recorder",
    "voxless.transcriber",
    "voxless.tray",
    "voxless.ui_window",
    "voxless.icons",
    "voxless.toast",
    "voxless.overlay",
    "voxless.sounds",
    "voxless.ai_actions",
    "voxless.frontmost",
    "voxless.permissions",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtNetwork",
]

a = Analysis(
    [str(ROOT / "voxless_app.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

is_mac = sys.platform == "darwin"
is_win = sys.platform.startswith("win")

icon_path = None
if is_mac:
    candidate = ROOT / "assets" / "voxless.icns"
    if candidate.exists():
        icon_path = str(candidate)
elif is_win:
    candidate = ROOT / "assets" / "voxless.ico"
    if candidate.exists():
        icon_path = str(candidate)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="voxless",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=icon_path,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="voxless",
)

if is_mac:
    app = BUNDLE(
        coll,
        name="voxless.app",
        icon=icon_path,
        bundle_identifier="co.lumigamher.voxless",
        info_plist={
            "CFBundleName": "voxless",
            "CFBundleDisplayName": "voxless",
            "CFBundleVersion": "0.2.1",
            "CFBundleShortVersionString": "0.2.1",
            "LSUIElement": False,
            "LSMultipleInstancesProhibited": True,
            "NSMicrophoneUsageDescription": "voxless graba audio del micrófono para transcribir tu dictado localmente.",
            "NSAppleEventsUsageDescription": "voxless usa eventos del sistema para pegar la transcripción.",
        },
    )
