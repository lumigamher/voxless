"""Capture / restore the foreground app so Cmd+V (or Ctrl+V) lands in
whatever app the user was using when they pressed the hotkey — not in
voxless, in case our overlay or window briefly took focus.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

log = logging.getLogger(__name__)


def _own_pid() -> int:
    import os
    return os.getpid()


def get_frontmost() -> Any:
    """Return an opaque platform-specific handle representing the currently
    frontmost app, or None if unavailable / if voxless itself is frontmost.

    We deliberately never capture our own pid — restoring "voxless to the
    front" later would re-open our main window and steal the cursor."""
    if sys.platform == "darwin":
        try:
            from AppKit import NSWorkspace  # type: ignore
            ws = NSWorkspace.sharedWorkspace()
            app = ws.frontmostApplication()
            if app is None:
                return None
            pid = int(app.processIdentifier())
            if pid == _own_pid():
                return None
            bundle = (app.bundleIdentifier() or "").lower()
            if "voxless" in bundle:
                return None
            return ("macos", pid)
        except Exception:
            log.debug("frontmost: NSWorkspace probe failed", exc_info=True)
            return None
    if sys.platform.startswith("win"):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd == 0:
                return None
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buf, length)
            if "voxless" in (buf.value or "").lower():
                return None
            return ("win", int(hwnd))
        except Exception:
            log.debug("frontmost: GetForegroundWindow failed", exc_info=True)
            return None
    return None


def is_voxless_frontmost() -> bool:
    """True if voxless itself currently owns the focused app — meaning we
    almost certainly stole focus and need to put it back before pasting."""
    if sys.platform == "darwin":
        try:
            from AppKit import NSWorkspace  # type: ignore
            front = NSWorkspace.sharedWorkspace().frontmostApplication()
            if front is None:
                return False
            bundle = front.bundleIdentifier() or ""
            return bundle == "co.lumigamher.voxless" or bundle.endswith(".voxless")
        except Exception:
            return False
    if sys.platform.startswith("win"):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd == 0:
                return False
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buf, length)
            return "voxless" in buf.value.lower()
        except Exception:
            return False
    return False


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
