"""Cross-platform permission detection + deep-links to system settings.

On macOS we surface Accessibility, Input Monitoring, and Microphone.
On Windows we link to the Microphone privacy pane (no programmatic
gate is needed for our other features).
"""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

log = logging.getLogger(__name__)

Status = Literal["granted", "denied", "unknown"]


@dataclass
class Permission:
    key: str
    title: str
    description: str
    detect: Callable[[], Status]
    open_settings: Callable[[], None]
    request: Callable[[], None] | None = None
    request_label: str = "Solicitar acceso"


def _open_url(url: str) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", url])
    elif sys.platform.startswith("win"):
        subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
    else:
        subprocess.Popen(["xdg-open", url])


def _macos_accessibility() -> Status:
    try:
        from ApplicationServices import AXIsProcessTrusted
        return "granted" if AXIsProcessTrusted() else "denied"
    except Exception:
        log.debug("AXIsProcessTrusted unavailable", exc_info=True)
        return "unknown"


def _macos_input_monitoring() -> Status:
    try:
        from Quartz import (
            kCGEventTapOptionListenOnly,
            kCGHeadInsertEventTap,
            CGEventTapCreate,
            kCGSessionEventTap,
            kCGEventKeyDown,
        )

        mask = 1 << kCGEventKeyDown
        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            mask,
            lambda *_args: None,
            None,
        )
        if tap is None:
            return "denied"
        try:
            from CoreFoundation import CFMachPortInvalidate
            CFMachPortInvalidate(tap)
        except Exception:
            pass
        return "granted"
    except Exception:
        log.debug("CGEventTapCreate probe failed", exc_info=True)
        return "unknown"


def _request_macos_accessibility() -> None:
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
        AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
    except Exception:
        log.exception("AXIsProcessTrustedWithOptions failed; opening Settings as fallback")
        _open_url("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")


def _request_macos_microphone() -> None:
    try:
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio  # type: ignore
        AVCaptureDevice.requestAccessForMediaType_completionHandler_(
            AVMediaTypeAudio, lambda granted: log.info("Mic access granted=%s", granted)
        )
    except Exception:
        log.exception("AVCaptureDevice.requestAccess failed; opening Settings as fallback")
        _open_url("x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone")


def _macos_microphone() -> Status:
    try:
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio  # type: ignore
        st = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
        # 0=notDetermined, 1=restricted, 2=denied, 3=authorized
        if st == 3:
            return "granted"
        if st in (1, 2):
            return "denied"
        return "unknown"
    except Exception:
        log.debug("AVCaptureDevice unavailable", exc_info=True)
        return "unknown"


def _open_mac(pane: str) -> Callable[[], None]:
    return lambda: _open_url(f"x-apple.systempreferences:com.apple.preference.security?{pane}")


def _open_win(uri: str) -> Callable[[], None]:
    return lambda: _open_url(uri)


def _windows_microphone() -> Status:
    return "unknown"  # Win 10+ rarely blocks at runtime; visual cue only


def list_permissions() -> list[Permission]:
    if sys.platform == "darwin":
        return [
            Permission(
                key="accessibility",
                title="Accesibilidad",
                description="Necesario para escuchar el hotkey global y simular ⌘V al pegar.",
                detect=_macos_accessibility,
                open_settings=_open_mac("Privacy_Accessibility"),
                request=_request_macos_accessibility,
                request_label="Solicitar acceso",
            ),
            Permission(
                key="input_monitoring",
                title="Monitoreo de entrada",
                description="Permite a voxless detectar la tecla configurada desde cualquier app.",
                detect=_macos_input_monitoring,
                open_settings=_open_mac("Privacy_ListenEvent"),
            ),
            Permission(
                key="microphone",
                title="Micrófono",
                description="Para grabar tu dictado y transcribirlo localmente.",
                detect=_macos_microphone,
                open_settings=_open_mac("Privacy_Microphone"),
                request=_request_macos_microphone,
                request_label="Solicitar acceso",
            ),
        ]
    if sys.platform.startswith("win"):
        return [
            Permission(
                key="microphone",
                title="Micrófono",
                description="Permite a voxless usar tu micrófono para dictado.",
                detect=_windows_microphone,
                open_settings=_open_win("ms-settings:privacy-microphone"),
            ),
        ]
    return []
