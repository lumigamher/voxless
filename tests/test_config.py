from __future__ import annotations

from pathlib import Path

import pytest

from voxless.config import Config, DEFAULT_CONFIG_TOML, load_config


def test_defaults_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")
    cfg = load_config(p)
    assert cfg.hotkey == "right_option"
    assert cfg.whisper.model == "small"
    assert cfg.ollama.enabled is True
    assert cfg.ollama.model == "gemma3:1b"
    assert cfg.paste.auto_paste is True


def test_partial_overrides(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text(
        """
hotkey = "f5"
[whisper]
model = "tiny"
[ollama]
model = "llama3.1:8b"
""",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.hotkey == "f5"
    assert cfg.whisper.model == "tiny"
    assert cfg.whisper.language == "es"  # default preserved
    assert cfg.ollama.model == "llama3.1:8b"
    assert cfg.ollama.enabled is True


def test_rejects_unknown_whisper_model(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text(
        """
[whisper]
model = "nonexistent"
""",
        encoding="utf-8",
    )
    with pytest.raises(Exception):
        load_config(p)


def test_min_record_ms_must_be_non_negative() -> None:
    with pytest.raises(Exception):
        Config(min_record_ms=-1)
