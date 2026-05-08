from __future__ import annotations

from pathlib import Path

from voxless.config import Config, load_config, save_config, save_prompt


def test_save_config_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    cfg = Config()
    cfg.whisper.model = "tiny"
    cfg.ollama.model = "llama3.1:8b"
    cfg.ollama.timeout_s = 12.5
    cfg.paste.auto_paste = False
    save_config(cfg, p)
    reloaded = load_config(p)
    assert reloaded.whisper.model == "tiny"
    assert reloaded.ollama.model == "llama3.1:8b"
    assert reloaded.ollama.timeout_s == 12.5
    assert reloaded.paste.auto_paste is False


def test_save_prompt_persists(tmp_path: Path) -> None:
    p = tmp_path / "prompt.md"
    save_prompt("hello\n", p)
    assert p.read_text(encoding="utf-8") == "hello\n"


def test_save_config_handles_quotes(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    cfg = Config()
    cfg.ollama.url = 'http://example.com/"weird"'
    save_config(cfg, p)
    reloaded = load_config(p)
    assert reloaded.ollama.url == 'http://example.com/"weird"'
