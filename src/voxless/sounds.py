"""Tiny synthesized feedback sounds — bubble-plop start, soft thud stop.

Played non-blocking through sounddevice on the user's default audio output.
Synth lives in pure numpy so we don't bundle any audio assets.
"""

from __future__ import annotations

import logging
import threading

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 44_100


def _bubble(freq_start: float, freq_end: float,
            duration: float = 0.14, gain: float = 0.45) -> np.ndarray:
    """A short wet "plop" — sine sweep with exponential decay + soft attack."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0.0, duration, n, endpoint=False, dtype=np.float32)

    # frequency glide — exponential interpolation feels more organic
    freq = freq_start * np.power(freq_end / freq_start, t / duration)
    phase = 2.0 * np.pi * np.cumsum(freq) / SAMPLE_RATE

    fundamental = np.sin(phase)
    second = 0.30 * np.sin(2.0 * phase)
    third = 0.10 * np.sin(3.0 * phase)
    wave = fundamental + second + third

    attack = 1.0 - np.exp(-t / 0.004)         # 4 ms attack
    decay = np.exp(-t / 0.045)                 # 45 ms decay
    envelope = (attack * decay).astype(np.float32)

    return (wave * envelope * gain).astype(np.float32)


_START = _bubble(180.0, 320.0, duration=0.14, gain=0.42)
_STOP  = _bubble(320.0, 160.0, duration=0.16, gain=0.38)


def _play(sample: np.ndarray) -> None:
    try:
        import sounddevice as sd  # local import — heavy dep
        sd.play(sample, samplerate=SAMPLE_RATE, blocking=False)
    except Exception:
        log.exception("Failed to play feedback sound")


def play_start() -> None:
    threading.Thread(target=_play, args=(_START,), daemon=True).start()


def play_stop() -> None:
    threading.Thread(target=_play, args=(_STOP,), daemon=True).start()
