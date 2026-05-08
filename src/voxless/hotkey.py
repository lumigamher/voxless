"""Global push-to-talk hotkey listener.

Supports a single named key (e.g. ``"right_option"``, ``"f5"``) or a combo
(e.g. ``"<ctrl>+<shift>+space"``). Combos are tracked manually so we can
fire press/release events for true push-to-talk behavior.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from pynput import keyboard

log = logging.getLogger(__name__)

_NAMED_KEYS: dict[str, Any] = {
    "alt": keyboard.Key.alt,
    "alt_l": keyboard.Key.alt_l,
    "alt_r": keyboard.Key.alt_r,
    "left_option": keyboard.Key.alt_l,
    "right_option": keyboard.Key.alt_r,
    "option": keyboard.Key.alt,
    "cmd": keyboard.Key.cmd,
    "cmd_l": keyboard.Key.cmd_l,
    "cmd_r": keyboard.Key.cmd_r,
    "ctrl": keyboard.Key.ctrl,
    "ctrl_l": keyboard.Key.ctrl_l,
    "ctrl_r": keyboard.Key.ctrl_r,
    "shift": keyboard.Key.shift,
    "shift_l": keyboard.Key.shift_l,
    "shift_r": keyboard.Key.shift_r,
    "fn": getattr(keyboard.Key, "fn", None),
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
    "esc": keyboard.Key.esc,
    "caps_lock": keyboard.Key.caps_lock,
}
for n in range(1, 21):
    name = f"f{n}"
    if hasattr(keyboard.Key, name):
        _NAMED_KEYS[name] = getattr(keyboard.Key, name)


def _resolve_named_key(name: str) -> Any:
    name = name.strip().lower()
    if name in _NAMED_KEYS and _NAMED_KEYS[name] is not None:
        return _NAMED_KEYS[name]
    if len(name) == 1:
        return keyboard.KeyCode.from_char(name)
    raise ValueError(f"Unknown hotkey: {name!r}")


def _key_matches(target: Any, event_key: Any) -> bool:
    if target == event_key:
        return True
    target_name = getattr(target, "name", None)
    event_name = getattr(event_key, "name", None)
    if target_name and event_name and target_name == event_name:
        return True
    return False


class HotkeyListener:
    """Push-to-talk listener.

    Single-key mode: fires ``on_press`` once when the key transitions to down
    (auto-repeat is suppressed) and ``on_release`` when it transitions to up.

    Combo mode: fires ``on_press`` once when ALL keys in the combo are held
    simultaneously, and ``on_release`` when ANY of them is released.
    """

    def __init__(
        self,
        spec: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        self._on_press = on_press
        self._on_release = on_release
        self._listener: keyboard.Listener | None = None

        if "+" in spec:
            self._combo: list[Any] = [
                _resolve_named_key(part.strip("<> ")) for part in spec.split("+")
            ]
            self._held: set[int] = set()
            self._is_active = False
        else:
            self._combo = [_resolve_named_key(spec)]
            self._held = set()
            self._is_active = False

    def _is_combo_key(self, key: Any) -> int | None:
        for i, target in enumerate(self._combo):
            if _key_matches(target, key):
                return i
        return None

    def _handle_press(self, key: Any) -> None:
        idx = self._is_combo_key(key)
        if idx is None:
            return
        self._held.add(idx)
        if not self._is_active and len(self._held) == len(self._combo):
            self._is_active = True
            try:
                self._on_press()
            except Exception:
                log.exception("on_press handler raised")

    def _handle_release(self, key: Any) -> None:
        idx = self._is_combo_key(key)
        if idx is None:
            return
        self._held.discard(idx)
        if self._is_active:
            self._is_active = False
            try:
                self._on_release()
            except Exception:
                log.exception("on_release handler raised")

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.daemon = True
        self._listener.start()
        log.info("Hotkey listener started: combo=%s", [str(k) for k in self._combo])

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def update(self, spec: str) -> None:
        was_running = self._listener is not None
        self.stop()
        if "+" in spec:
            self._combo = [_resolve_named_key(part.strip("<> ")) for part in spec.split("+")]
        else:
            self._combo = [_resolve_named_key(spec)]
        self._held = set()
        self._is_active = False
        if was_running:
            self.start()
