"""Ollama /api/chat client with timeout + raw-fallback behavior."""

from __future__ import annotations

import logging
import re

import httpx

from .config import OllamaConfig

log = logging.getLogger(__name__)

# Common LLM preamble openings we strip even if the prompt forbade them.
_PREAMBLE_RE = re.compile(
    r"""^\s*(?:
        (?:bien|bueno|claro|listo|perfecto|okay|sure|of\s+course|certainly)
        \s*[,!.\-—:]?\s*
    )?
    (?:
        (?:aqu[ií](?:\s+(?:está|tienes|va))?|here(?:'s|\s+(?:is|you\s+go))?)
        \s+(?:la|el|the)?\s*
        (?:transcripción|texto|mensaje|cleaned|version|result)?
        [^:\n]{0,40}:?\s*
    )?
    (?:^|\n)?
    """,
    re.IGNORECASE | re.VERBOSE,
)

_QUOTE_PAIRS = [('"', '"'), ("'", "'"), ("«", "»"), ("“", "”"), ("‘", "’")]


def _strip_preamble(text: str) -> str:
    """Remove conversational preamble + wrapping quotes the LLM may add."""
    if not text:
        return text
    out = text.strip()
    # Drop a leading line if it looks like meta ("Aquí tienes:", "Bien...")
    first_line = out.split("\n", 1)[0].strip()
    if (
        first_line.lower().startswith(
            ("bien,", "bueno,", "claro,", "listo,", "perfecto,",
             "okay,", "sure,", "aquí está", "aquí tienes",
             "here is", "here's", "here you go", "of course")
        )
        and first_line.endswith(":")
    ) or _PREAMBLE_RE.match(first_line):
        rest = out.split("\n", 1)
        if len(rest) > 1 and rest[1].strip():
            out = rest[1].strip()
    # Strip wrapping quote pairs
    for ql, qr in _QUOTE_PAIRS:
        if out.startswith(ql) and out.endswith(qr) and len(out) > 1:
            out = out[1:-1].strip()
            break
    return out


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
            cleaned = _strip_preamble(cleaned)
            if not cleaned:
                return text
            return cleaned
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Ollama call failed (%s); falling back to raw text", exc)
            return text

    def transform(self, text: str, system_prompt: str) -> str:
        """Same as clean() but with a different system prompt — used for
        AI actions (Improve / Summarize / Translate) on history items."""
        return self.clean(text, system_prompt)
