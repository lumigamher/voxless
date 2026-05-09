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

        # Vocabulary hint for short, conversational dictation. The first
        # transcription pass benefits from priming with sample words so
        # the LM doesn't insert capital-letter Hallucinations on common
        # phrases. Kept short to avoid biasing real speech.
        initial_prompt = (
            "Hola. Buenos días. ¿Cómo estás? voxless, transcripción, dictado, "
            "código, función, archivo, configuración, modelo, prompt, sí, no, "
            "claro, vale, ok, gracias."
            if (self._cfg.language or "").lower().startswith("es")
            else None
        )

        segments, _info = self._model.transcribe(
            audio,
            language=self._cfg.language,
            task="transcribe",
            beam_size=8,
            best_of=5,
            patience=1.0,
            length_penalty=1.0,
            temperature=[0.0, 0.2, 0.4, 0.6, 0.8],
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.55,
            condition_on_previous_text=False,
            initial_prompt=initial_prompt,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 400,
            },
        )
        text = "".join(seg.text for seg in segments).strip()
        log.debug("Transcribed %d chars", len(text))
        return text
