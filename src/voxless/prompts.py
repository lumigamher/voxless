"""Load the active system prompt for the LLM cleanup step."""

from __future__ import annotations

from pathlib import Path

from .config import PROMPT_PATH, _bundled_prompt_text


def load_prompt(path: Path | None = None) -> str:
    target = path or PROMPT_PATH
    if target.exists():
        text = target.read_text(encoding="utf-8").strip()
        if text:
            return text
    return _bundled_prompt_text().strip()
