"""Clipboard + simulated ⌘V auto-paste."""

from __future__ import annotations

import logging
import threading
import time

import pyperclip
from pynput.keyboard import Controller, Key

from .config import PasteConfig

log = logging.getLogger(__name__)


class Paster:
    def __init__(self, cfg: PasteConfig, controller: Controller | None = None) -> None:
        self._cfg = cfg
        self._controller = controller or Controller()

    def paste(self, text: str) -> None:
        if not text:
            return
        previous = ""
        try:
            previous = pyperclip.paste() or ""
        except Exception:
            log.debug("Could not read previous clipboard", exc_info=True)

        try:
            pyperclip.copy(text)
        except Exception:
            log.exception("Failed to set clipboard; aborting paste")
            return

        if not self._cfg.auto_paste:
            log.info("Auto-paste disabled — text left on clipboard (%d chars)", len(text))
            return

        time.sleep(self._cfg.paste_delay_ms / 1000.0)
        try:
            self._send_cmd_v()
        except Exception:
            log.exception("Failed to send ⌘V; text remains on clipboard")
            return

        if self._cfg.restore_clipboard and previous:
            threading.Timer(0.5, self._restore, args=(previous,)).start()

    def _send_cmd_v(self) -> None:
        with self._controller.pressed(Key.cmd):
            self._controller.press("v")
            self._controller.release("v")

    @staticmethod
    def _restore(previous: str) -> None:
        try:
            pyperclip.copy(previous)
        except Exception:
            log.debug("Failed to restore clipboard", exc_info=True)
