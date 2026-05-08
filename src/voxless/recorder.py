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
        if self._is_recording:
            return
        with self._lock:
            self._chunks = []
            self._is_recording = True
        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
        )
        self._stream.start()
        log.debug("Recording started")

    def stop(self) -> np.ndarray:
        if not self._is_recording:
            return np.zeros(0, dtype=np.float32)
        with self._lock:
            self._is_recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            audio = np.concatenate(self._chunks, axis=0).flatten().astype(np.float32)
            self._chunks = []
        log.debug("Recording stopped: %d samples (%.2fs)", len(audio), len(audio) / self._sample_rate)
        return audio

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
