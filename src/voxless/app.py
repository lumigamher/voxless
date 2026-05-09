"""Orchestrator: wires hotkey → recorder → transcriber → llm → paster.

Qt's QApplication owns the main thread and event loop. The tray and the
main window live inside it. A worker thread drains an event queue so
audio I/O and model inference never block the UI.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Literal

from PySide6.QtCore import QObject, QTimer, Signal

from .config import Config, load_config
from .hotkey import HotkeyListener
from .llm import OllamaClient
from .paster import Paster
from .prompts import load_prompt
from .recorder import SAMPLE_RATE, Recorder
from . import frontmost, sounds
from .transcriber import Transcriber

log = logging.getLogger(__name__)

State = Literal["idle", "recording", "processing", "error"]
Event = Literal["press", "release", "shutdown"]


class AppSignals(QObject):
    state_changed = Signal(str)
    transcribed = Signal(str, str)  # raw, clean
    error = Signal(str)


class App:
    """Backend orchestrator. UI is wired externally via `signals`."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._state: State = "idle"
        self._events: queue.Queue[Event] = queue.Queue()
        self._record_started_at: float | None = None

        self._recorder = Recorder()
        self._transcriber = Transcriber(cfg.whisper)
        self._llm = OllamaClient(cfg.ollama)
        self._paster = Paster(cfg.paste)
        self._prompt = load_prompt()
        self._frontmost = None

        self.signals = AppSignals()

        self._hotkey = HotkeyListener(
            cfg.hotkey,
            on_press=lambda: self._events.put("press"),
            on_release=lambda: self._events.put("release"),
        )

        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run_worker, daemon=True, name="voxless-worker")

    @property
    def recorder(self) -> Recorder:
        return self._recorder

    def start_background(self) -> None:
        self._hotkey.start()
        self._worker.start()
        log.info("voxless backend ready — hotkey: %s", self._cfg.hotkey)

    def shutdown(self) -> None:
        log.info("Shutting down")
        self._stop.set()
        try:
            self._hotkey.stop()
        except Exception:
            log.exception("Hotkey stop failed")
        self._events.put("shutdown")

    def reload_config(self) -> None:
        try:
            new_cfg = load_config()
        except Exception:
            log.exception("Failed to reload config — keeping previous values")
            return

        old_cfg = self._cfg
        self._cfg = new_cfg

        try:
            if (
                old_cfg.ollama.url != new_cfg.ollama.url
                or old_cfg.ollama.timeout_s != new_cfg.ollama.timeout_s
                or old_cfg.ollama.enabled != new_cfg.ollama.enabled
                or old_cfg.ollama.model != new_cfg.ollama.model
                or old_cfg.ollama.temperature != new_cfg.ollama.temperature
            ):
                self._llm = OllamaClient(new_cfg.ollama)
        except Exception:
            log.exception("Failed to swap Ollama client — keeping previous")

        try:
            if (
                old_cfg.paste.auto_paste != new_cfg.paste.auto_paste
                or old_cfg.paste.paste_delay_ms != new_cfg.paste.paste_delay_ms
                or old_cfg.paste.restore_clipboard != new_cfg.paste.restore_clipboard
            ):
                self._paster = Paster(new_cfg.paste)
        except Exception:
            log.exception("Failed to swap Paster — keeping previous")

        try:
            if (
                self._transcriber.model_name != new_cfg.whisper.model
                or self._transcriber.compute_type != new_cfg.whisper.compute_type
            ):
                self._transcriber = Transcriber(new_cfg.whisper)
        except Exception:
            log.exception("Failed to swap Whisper transcriber — keeping previous")

        try:
            if old_cfg.hotkey != new_cfg.hotkey:
                self._hotkey.update(new_cfg.hotkey)
                log.info("Hotkey rebound: %s -> %s", old_cfg.hotkey, new_cfg.hotkey)
        except Exception:
            log.exception("Failed to rebind hotkey — keeping previous")

        log.info("Config reloaded")

    def reload_prompt(self) -> None:
        try:
            self._prompt = load_prompt()
        except Exception:
            log.exception("Failed to reload prompt")

    def _set_state(self, state: State) -> None:
        if state == self._state:
            return
        self._state = state
        self.signals.state_changed.emit(state)

    def _run_worker(self) -> None:
        while not self._stop.is_set():
            try:
                event = self._events.get(timeout=0.5)
            except queue.Empty:
                continue
            if event == "shutdown":
                return
            try:
                self._handle_event(event)
            except Exception:
                log.exception("Worker failed handling %s", event)
                self._set_state("error")
                self.signals.error.emit("Worker error — revisa logs")
                threading.Timer(3.0, lambda: self._set_state("idle")).start()

    def _handle_event(self, event: Event) -> None:
        mode = self._cfg.hotkey_mode

        if mode == "toggle":
            # Press toggles between idle and recording. Release is ignored.
            if event != "press":
                return
            if self._state == "idle":
                self._recorder.start()
                self._record_started_at = time.monotonic()
                self._set_state("recording")
                return
            if self._state == "recording":
                event = "release"  # fall through to stop logic
            else:
                return

        if event == "press":
            if self._state != "idle":
                return
            self._frontmost = frontmost.get_frontmost()
            self._recorder.start()
            self._record_started_at = time.monotonic()
            self._set_state("recording")
            if self._cfg.sound_feedback:
                sounds.play_start()
            return

        if event == "release":
            if self._state != "recording":
                return
            audio = self._recorder.stop()
            if self._cfg.sound_feedback:
                sounds.play_stop()
            duration_ms = int((time.monotonic() - (self._record_started_at or 0)) * 1000)
            self._record_started_at = None

            min_ms = self._cfg.min_record_ms
            if duration_ms < min_ms or audio.size < SAMPLE_RATE * min_ms / 1000:
                log.info("Ignoring short recording (%dms)", duration_ms)
                self._set_state("idle")
                return

            self._set_state("processing")
            text_raw = self._transcriber.transcribe(audio)
            if not text_raw:
                self._set_state("idle")
                return
            log.info("Transcribed: %s", text_raw)

            text_clean = (
                self._llm.clean(text_raw, self._prompt)
                if self._cfg.ollama.enabled
                else text_raw
            )
            log.info("Cleaned: %s", text_clean)

            self.signals.transcribed.emit(text_raw, text_clean)

            # Only restore the captured app if voxless is currently in the
            # foreground — otherwise the user is already in their target
            # app and we should leave focus exactly where it is (preserves
            # cursor position inside whatever input they clicked).
            if (
                self._frontmost is not None
                and frontmost.is_voxless_frontmost()
            ):
                log.info("voxless took focus — restoring previous app before paste")
                frontmost.restore(self._frontmost)
                time.sleep(0.15)
            self._paster.paste(text_clean)
            self._frontmost = None
            self._set_state("idle")
