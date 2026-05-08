"""Ollama /api/chat client with timeout + raw-fallback behavior."""

from __future__ import annotations

import logging

import httpx

from .config import OllamaConfig

log = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, cfg: OllamaConfig, client: httpx.Client | None = None) -> None:
        self._cfg = cfg
        self._client = client or httpx.Client(timeout=cfg.timeout_s)

    def clean(self, text: str, system_prompt: str) -> str:
        """Send text + system prompt to Ollama. On any failure, return ``text`` unchanged."""
        if not text.strip():
            return text
        if not self._cfg.enabled:
            return text
        url = f"{self._cfg.url.rstrip('/')}/api/chat"
        payload = {
            "model": self._cfg.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "stream": False,
            "options": {"temperature": self._cfg.temperature},
        }
        try:
            r = self._client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            cleaned = data.get("message", {}).get("content", "").strip()
            if not cleaned:
                log.warning("Ollama returned empty content; falling back to raw text")
                return text
            return cleaned
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Ollama call failed (%s); falling back to raw text", exc)
            return text
