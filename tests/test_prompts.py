from __future__ import annotations

from pathlib import Path

from voxless.prompts import load_prompt


def test_user_prompt_wins(tmp_path: Path) -> None:
    p = tmp_path / "prompt.md"
    p.write_text("USER PROMPT", encoding="utf-8")
    assert load_prompt(p) == "USER PROMPT"


def test_falls_back_to_bundled_when_missing(tmp_path: Path) -> None:
    p = tmp_path / "missing.md"
    text = load_prompt(p)
    assert "transcription cleanup assistant" in text.lower()


def test_falls_back_when_empty(tmp_path: Path) -> None:
    p = tmp_path / "prompt.md"
    p.write_text("   \n  ", encoding="utf-8")
    text = load_prompt(p)
    assert "transcription cleanup assistant" in text.lower()
