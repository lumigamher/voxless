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
        self._target_app = None  # captured via frontmost.get_frontmost on press

        self.signals = AppSignals()

        self._hotkey = HotkeyListener(
            cfg.hotkey,
            on_press=lambda: self._events.put("press"),
            on_release=lambda: self._events.put("release"),
        )

        self._stop = threading.Event()
        # Heartbeat: the worker stamps this at the top of every loop tick.
        # The watchdog inspects it to decide whether the worker is alive or
        # wedged inside _handle_event (e.g. PortAudio hang in recorder.stop).
        self._worker_heartbeat: float = time.monotonic()
        self._worker_lock = threading.Lock()
        self._worker = self._spawn_worker()
        self._watchdog = threading.Thread(target=self._run_watchdog, daemon=True, name="voxless-watchdog")

    @property
    def recorder(self) -> Recorder:
        return self._recorder

    def start_background(self) -> None:
        self._hotkey.start()
        # Worker thread was already started in __init__ via _spawn_worker
        # so it can be respawned by the watchdog at any time without a
        # lifecycle mismatch.
        self._watchdog.start()
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

    def _spawn_worker(self) -> threading.Thread:
        t = threading.Thread(target=self._run_worker, daemon=True, name="voxless-worker")
        t.start()
        return t

    def _force_recover(self, reason: str) -> None:
        """Bypass the worker queue and reset state directly. Called by the
        watchdog when it detects that the worker can't recover on its own
        (PortAudio hang, missed release, deadlock). Safe to call from any
        thread — Recorder.abort() is thread-safe and signals are queued."""
        log.warning("watchdog: force-recovering — %s", reason)
        try:
            self._recorder.abort()
        except Exception:
            log.exception("recorder.abort() raised during force-recovery")
        # Drain any stale press/release events the user (or earlier watchdog
        # ticks) queued up while the worker was wedged. Leaving them in the
        # queue would cause spurious recordings the moment the worker wakes.
        drained = 0
        while True:
            try:
                self._events.get_nowait()
                drained += 1
            except queue.Empty:
                break
        if drained:
            log.warning("watchdog: drained %d stale events from queue", drained)
        self._target_app = None
        self._record_started_at = None
        self._set_state("idle")

    def _replace_worker_if_dead(self) -> None:
        """If the worker thread looks dead (no heartbeat for ~60s and not
        alive, OR alive but stuck inside _handle_event), spawn a fresh one.
        The old thread leaks if it's still alive — the OS will reclaim it
        when the process exits. This is the panic exit path; under normal
        operation the worker is always responsive."""
        worker = self._worker
        with self._worker_lock:
            stale = time.monotonic() - self._worker_heartbeat
            if not worker.is_alive():
                log.error("worker thread died — respawning (heartbeat stale %.1fs)", stale)
                self._worker_heartbeat = time.monotonic()
                self._worker = self._spawn_worker()
            elif stale > 60.0:
                log.error(
                    "worker thread heartbeat stale for %.1fs — spawning replacement; "
                    "old thread leaked", stale,
                )
                self._worker_heartbeat = time.monotonic()
                self._worker = self._spawn_worker()

    def _run_watchdog(self) -> None:
        """Background watchdog with teeth. Two-stage recovery:

        Stage 1 (stuck > 30s): the worker may have simply missed a release
        event. Force-recover directly — abort the recorder, drop the queue,
        reset state. This bypasses the worker entirely, so it works even if
        the worker is blocked inside recorder.stop().

        Stage 2 (worker heartbeat stale > 60s): the worker thread is dead
        or wedged in a way our recover couldn't fix (e.g. blocked on a
        Python GIL contention, an Ollama timeout, etc). Spawn a replacement
        worker and abandon the old one to OS-level reclamation."""
        while not self._stop.wait(2.0):
            if self._state == "recording" and self._record_started_at is not None:
                age = time.monotonic() - self._record_started_at
                if age > 30.0:
                    self._force_recover(f"stuck recording for {age:.1f}s")
                    self._replace_worker_if_dead()
                    continue
            # Even if state isn't 'recording', a dead worker is fatal —
            # no event will ever be processed again. Detect and respawn.
            self._replace_worker_if_dead()

    def _run_worker(self) -> None:
        while not self._stop.is_set():
            with self._worker_lock:
                self._worker_heartbeat = time.monotonic()
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
            # Pressing the hotkey AGAIN while already recording means the
            # OS dropped a release event (or the user wants to forcibly
            # end this dictation). Treat it as a release — definitive stop.
            if self._state == "recording":
                log.warning("press while recording — forcing release")
                event = "release"  # fall through
            elif self._state != "idle":
                log.debug("press ignored — state=%s", self._state)
                return
            else:
                # Normal press path.
                self._target_app = frontmost.get_frontmost()
                if self._target_app:
                    log.info("captured target app: %s", self._target_app)
                self._recorder.start()
                self._record_started_at = time.monotonic()
                self._set_state("recording")
                if self._cfg.sound_feedback:
                    sounds.play_start()
                return

        if event == "release":
            if self._state != "recording":
                return
            # try/finally guarantees we always return to idle, even if
            # transcription / Ollama / paste raises. No more "stuck in REC".
            try:
                # Pin the start time and flip state BEFORE recorder.stop()
                # so the watchdog (which only triggers on state==recording)
                # stops re-firing the moment we acknowledge the release.
                # Otherwise a slow PortAudio close would let the watchdog
                # spam the queue with phantom release events.
                started_at = self._record_started_at or time.monotonic()
                self._record_started_at = None
                self._set_state("processing")
                audio = self._recorder.stop()
                if self._cfg.sound_feedback:
                    sounds.play_stop()
                duration_ms = int((time.monotonic() - started_at) * 1000)

                min_ms = self._cfg.min_record_ms
                if duration_ms < min_ms or audio.size < SAMPLE_RATE * min_ms / 1000:
                    log.info("Ignoring short recording (%dms)", duration_ms)
                    return

                text_raw = self._transcriber.transcribe(audio)
                if not text_raw:
                    return
                log.info("Transcribed: %s", text_raw)

                text_clean = (
                    self._llm.clean(text_raw, self._prompt)
                    if self._cfg.ollama.enabled
                    else text_raw
                )
                log.info("Cleaned: %s", text_clean)

                self.signals.transcribed.emit(text_raw, text_clean)

                # Paste strategy — defensive in depth so Cmd+V NEVER lands
                # in voxless itself:
                #  1. ALWAYS deactivate voxless first. macOS may have
                #     re-activated us when the overlay or another window
                #     became visible during dictation; this step undoes
                #     that without waiting for the AppKit auto-deactivate.
                #  2. If we captured a target app on press, activate it
                #     synchronously via osascript (with a 2 s timeout so a
                #     hung osascript can't block paste forever).
                #  3. Give the OS ~180 ms to actually switch focus.
                #  4. Last-line safety: verify that voxless is NOT the
                #     frontmost app right before pressing Cmd+V. If we
                #     still are (osascript failed, target app was buggy,
                #     etc), call frontmost.deactivate_self() to force a
                #     hide — Cmd+V then lands in whichever app macOS
                #     picks as the next-active one.
                if sys.platform == "darwin":
                    try:
                        from AppKit import NSApplication  # type: ignore
                        NSApplication.sharedApplication().deactivate()
                    except Exception:
                        log.debug("NSApp.deactivate before paste failed", exc_info=True)

                activated = False
                if self._target_app is not None:
                    try:
                        activated = frontmost.activate_app(self._target_app)
                    except Exception:
                        log.exception("activate_app raised; will fall back")

                time.sleep(0.18)

                if sys.platform == "darwin" and frontmost.is_voxless_frontmost():
                    log.warning(
                        "voxless still frontmost before paste (target_activated=%s) — forcing hide",
                        activated,
                    )
                    try:
                        frontmost.deactivate_self()
                        time.sleep(0.18)
                    except Exception:
                        log.exception("deactivate_self last-resort failed")

                self._paster.paste(text_clean)
            finally:
                self._target_app = None
                self._set_state("idle")
