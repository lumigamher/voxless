"""Microphone recorder: streams 16 kHz mono float32 into an in-memory buffer."""

from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np
import sounddevice as sd

log = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
CHANNELS = 1
DTYPE = "float32"


class Recorder:
    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self._sample_rate = sample_rate
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def _callback(self, indata: np.ndarray, frames: int, time: Any, status: Any) -> None:
        if status:
            log.debug("sounddevice status: %s", status)
        with self._lock:
            if self._is_recording:
                self._chunks.append(indata.copy())

    def start(self) -> None:
        # Force-clean any leftover stream from a prior aborted session.
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                log.debug("Cleanup of stale stream raised", exc_info=True)
            self._stream = None
        with self._lock:
            self._chunks = []
            self._is_recording = True
        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=CHANNELS,
                dtype=DTYPE,
                callback=self._callback,
            )
            self._stream.start()
            log.debug("Recording started")
        except Exception:
            log.exception("Failed to open input stream")
            with self._lock:
                self._is_recording = False
            raise

    def stop(self) -> np.ndarray:
        if not self._is_recording:
            return np.zeros(0, dtype=np.float32)
        with self._lock:
            self._is_recording = False
        self._close_stream_with_timeout(timeout_s=2.0)
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            audio = np.concatenate(self._chunks, axis=0).flatten().astype(np.float32)
            self._chunks = []
        log.debug("Recording stopped: %d samples (%.2fs)", len(audio), len(audio) / self._sample_rate)
        return audio

    def abort(self) -> None:
        """Force-stop the recorder from ANY thread without raising. Safe to
        call when stop() or the PortAudio stream is wedged. Discards captured
        audio (this is the panic exit path, not the happy path)."""
        with self._lock:
            self._is_recording = False
            self._chunks = []
        self._close_stream_with_timeout(timeout_s=2.0)

    def _close_stream_with_timeout(self, timeout_s: float) -> None:
        """Close the PortAudio stream in a side thread with a hard deadline.
        PortAudio on macOS occasionally hangs forever inside stream.stop()
        when the audio HAL deadlocks (Bluetooth disconnect, sample-rate
        renegotiation, USB device disappearance). If we don't time-bound the
        call, the worker thread freezes indefinitely. If the close hangs we
        leak the stream object — the OS will reclaim it when the process
        exits. The next start() will allocate a fresh one."""
        stream = self._stream
        if stream is None:
            return
        self._stream = None

        def _shutdown() -> None:
            try:
                stream.stop()
            except Exception:
                log.debug("stream.stop() raised during shutdown", exc_info=True)
            try:
                stream.close()
            except Exception:
                log.debug("stream.close() raised during shutdown", exc_info=True)

        worker = threading.Thread(target=_shutdown, daemon=True, name="voxless-stream-close")
        worker.start()
        worker.join(timeout=timeout_s)
        if worker.is_alive():
            log.warning("PortAudio stream close hung past %.1fs — leaking stream", timeout_s)

    def duration_so_far_ms(self) -> int:
        with self._lock:
            samples = sum(c.shape[0] for c in self._chunks)
        return int(samples * 1000 / self._sample_rate)

    def peak_recent(self, samples: int = 1600) -> float:
        with self._lock:
            if not self._chunks:
                return 0.0
            tail: list[np.ndarray] = []
            remaining = samples
            for chunk in reversed(self._chunks):
                tail.insert(0, chunk)
                remaining -= chunk.shape[0]
                if remaining <= 0:
                    break
            arr = np.concatenate(tail).flatten()
        if arr.size == 0:
            return 0.0
        return float(np.max(np.abs(arr[-samples:])))
