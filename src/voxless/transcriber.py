"""faster-whisper wrapper with lazy model loading."""

from __future__ import annotations

import logging

import numpy as np

from .config import WhisperConfig

log = logging.getLogger(__name__)


class Transcriber:
    def __init__(self, cfg: WhisperConfig) -> None:
        self._cfg = cfg
        self._model = None

    @property
    def model_name(self) -> str:
        return self._cfg.model

    @property
    def compute_type(self) -> str:
        return self._cfg.compute_type

    def _load_model(self):
        from faster_whisper import WhisperModel

        log.info("Loading Whisper model %r (compute=%s, device=%s) — first load downloads if needed", self._cfg.model, self._cfg.compute_type, self._cfg.device)
        self._model = WhisperModel(
            self._cfg.model,
            device=self._cfg.device,
            compute_type=self._cfg.compute_type,
        )
        log.info("Whisper model ready")

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        if self._model is None:
            self._load_model()
        assert self._model is not None
        segments, _info = self._model.transcribe(
            audio,
            language=self._cfg.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text = "".join(seg.text for seg in segments).strip()
        log.debug("Transcribed %d chars", len(text))
        return text
