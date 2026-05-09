"""Capture / restore the foreground app so Cmd+V (or Ctrl+V) lands in
whatever app the user was using when they pressed the hotkey — not in
voxless, in case our overlay or window briefly took focus.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

log = logging.getLogger(__name__)


def get_frontmost() -> Any:
    """Return an opaque platform-specific handle representing the currently
    frontmost app. Returns None if unavailable."""
    if sys.platform == "darwin":
        try:
            from AppKit import NSWorkspace  # type: ignore
            ws = NSWorkspace.sharedWorkspace()
            app = ws.frontmostApplication()
            if app is None:
                return None
            return ("macos", int(app.processIdentifier()))
        except Exception:
            log.debug("frontmost: NSWorkspace probe failed", exc_info=True)
            return None
    if sys.platform.startswith("win"):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd == 0:
                return None
            return ("win", int(hwnd))
        except Exception:
            log.debug("frontmost: GetForegroundWindow failed", exc_info=True)
            return None
    return None


def restore(handle: Any) -> bool:
    """Bring the given handle's app/window back to the foreground. Returns
    True if the call dispatched cleanly."""
    if not handle:
        return False
    platform, value = handle
    if platform == "macos":
        try:
            from AppKit import NSRunningApplication  # type: ignore
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(value)
            if app is None:
                return False
            # NSApplicationActivateIgnoringOtherApps = 1 << 1
            return bool(app.activateWithOptions_(1 << 1))
        except Exception:
            log.debug("frontmost: activateWithOptions failed", exc_info=True)
            return False
    if platform == "win":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetForegroundWindow(value)
            return True
        except Exception:
            log.debug("frontmost: SetForegroundWindow failed", exc_info=True)
            return False
    return False
