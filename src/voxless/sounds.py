"""Tiny synthesized feedback sounds — clean, percussive UI clicks.

Synth lives in pure numpy so we don't bundle any audio assets. Plays
non-blocking through sounddevice on the user's default audio output.
"""

from __future__ import annotations

import logging
import threading

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 44_100


def _click(freq: float,
           duration: float = 0.07,
           attack_ms: float = 1.5,
           decay_ms: float = 30.0,
           gain: float = 0.32,
           harmonic_mix: float = 0.18) -> np.ndarray:
    """A short percussive click — clean sine + a tiny amount of 2nd
    harmonic for sparkle. Tight attack-decay envelope keeps it
    crisp instead of bubble-like."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0.0, duration, n, endpoint=False, dtype=np.float32)

    phase = 2.0 * np.pi * freq * t
    fundamental = np.sin(phase)
    second = np.sin(2.0 * phase) * harmonic_mix
    wave = fundamental + second

    attack = 1.0 - np.exp(-t / (attack_ms / 1000.0))
    decay = np.exp(-t / (decay_ms / 1000.0))
    envelope = (attack * decay).astype(np.float32)

    return (wave * envelope * gain).astype(np.float32)


# Start: short, slightly higher pitch — feels like turning ON.
_START = _click(freq=720.0, duration=0.06, attack_ms=1.0,
                decay_ms=22.0, gain=0.30)

# Stop: half-step lower, slightly longer decay — feels like releasing.
_STOP = _click(freq=540.0, duration=0.07, attack_ms=1.0,
               decay_ms=28.0, gain=0.28)


def _play(sample: np.ndarray) -> None:
    try:
        import sounddevice as sd
        sd.play(sample, samplerate=SAMPLE_RATE, blocking=False)
    except Exception:
        log.exception("Failed to play feedback sound")


def play_start() -> None:
    threading.Thread(target=_play, args=(_START,), daemon=True).start()


def play_stop() -> None:
    threading.Thread(target=_play, args=(_STOP,), daemon=True).start()
