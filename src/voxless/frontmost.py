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
    """Return an opaque platform-specific handle for the currently-foreground
    app, or None if it's voxless / unavailable.

    macOS:   ("macos", pid, localized_name)
    Windows: ("win", hwnd)
    """
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
            name = str(app.localizedName() or "")
            return ("macos", pid, name)
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


def activate_app(handle: Any) -> bool:
    """Bring the captured app to the foreground without activating voxless.

    macOS: osascript "tell application X to activate" — runs synchronously
    with a hard 2 s timeout, so the caller knows whether activation
    actually completed before scheduling the Cmd+V. The previous Popen-
    and-forget version returned True even when osascript silently failed,
    which is how paste ended up in voxless on the second dictation.

    Windows: SetForegroundWindow on the captured HWND.
    """
    if not handle:
        return False
    if sys.platform == "darwin":
        try:
            import subprocess
            _platform, _pid, name = handle
            if not name:
                return False
            safe_name = name.replace('"', '')
            result = subprocess.run(
                ["osascript", "-e", f'tell application "{safe_name}" to activate'],
                timeout=2.0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                log.warning(
                    "activate_app: osascript exited %d for %r: %s",
                    result.returncode, safe_name,
                    result.stderr.decode("utf-8", "replace").strip() or "<no stderr>",
                )
                return False
            return True
        except subprocess.TimeoutExpired:
            log.warning("activate_app: osascript timed out activating %r", handle)
            return False
        except Exception:
            log.debug("activate_app: osascript failed", exc_info=True)
            return False
    if sys.platform.startswith("win"):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            _platform, hwnd = handle
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            log.debug("activate_app: SetForegroundWindow failed", exc_info=True)
            return False
    return False


def deactivate_self() -> bool:
    """Hide voxless if it's currently in the foreground so macOS hands
    focus back to the previously-active app. Cmd+V then lands there.

    This is more reliable than capture-and-restore because it leans on
    the OS to pick the right "next app" for us, instead of guessing
    which app/window/PID had focus when the hotkey fired."""
    if sys.platform == "darwin":
        try:
            from AppKit import NSApplication, NSWorkspace  # type: ignore
            ws = NSWorkspace.sharedWorkspace()
            front = ws.frontmostApplication()
            if front is None:
                return False
            bundle = (front.bundleIdentifier() or "").lower()
            pid = int(front.processIdentifier())
            if pid != _own_pid() and "voxless" not in bundle:
                # Not us — leave focus alone.
                return False
            # We're the frontmost app. Hide ourselves; macOS will give
            # focus to whatever the user was previously in.
            NSApplication.sharedApplication().hide_(None)
            return True
        except Exception:
            log.debug("deactivate_self: hide_ failed", exc_info=True)
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
            if "voxless" not in (buf.value or "").lower():
                return False
            # SW_MINIMIZE = 6 — minimizing returns focus to the next
            # window in z-order.
            user32.ShowWindow(hwnd, 6)
            return True
        except Exception:
            log.debug("deactivate_self: minimize failed", exc_info=True)
            return False
    return False


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
