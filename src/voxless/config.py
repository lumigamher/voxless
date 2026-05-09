"""Configuration loading and validation."""

from __future__ import annotations

import os
import shutil
import sys
import tomllib
from importlib import resources
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


def _default_config_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / ".config" / "voxless"
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "voxless"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "voxless"


CONFIG_DIR = _default_config_dir()
CONFIG_PATH = CONFIG_DIR / "config.toml"
PROMPT_PATH = CONFIG_DIR / "prompt.md"

DEFAULT_CONFIG_TOML = """\
hotkey = "right_option"
hotkey_mode = "hold"
min_record_ms = 250
sound_feedback = false
show_overlay = true
ui_language = "es"

[whisper]
model = "small"
language = "es"
compute_type = "int8"
device = "auto"

[ollama]
enabled = true
url = "http://localhost:11434"
model = "gemma3:1b"
timeout_s = 30
temperature = 0.2

[paste]
auto_paste = true
paste_delay_ms = 80
restore_clipboard = true
"""


class WhisperConfig(BaseModel):
    model: Literal["tiny", "base", "small", "medium", "large-v3"] = "small"
    language: str | None = "es"
    compute_type: Literal["int8", "int8_float16", "float16", "float32"] = "int8"
    device: Literal["auto", "cpu"] = "auto"


class OllamaConfig(BaseModel):
    enabled: bool = True
    url: str = "http://localhost:11434"
    model: str = "gemma3:1b"
    timeout_s: float = 30.0
    temperature: float = 0.2


class PasteConfig(BaseModel):
    auto_paste: bool = True
    paste_delay_ms: int = 80
    restore_clipboard: bool = True


HotkeyMode = Literal["hold", "toggle"]
UiLanguage = Literal["es", "en"]


class Config(BaseModel):
    hotkey: str = "right_option"
    hotkey_mode: HotkeyMode = "hold"
    min_record_ms: int = Field(250, ge=0)
    sound_feedback: bool = False
    show_overlay: bool = True
    ui_language: UiLanguage = "es"
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    paste: PasteConfig = Field(default_factory=PasteConfig)


def _bundled_prompt_text() -> str:
    try:
        return resources.files("voxless").joinpath("_data/default_prompt.md").read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        repo_prompt = Path(__file__).resolve().parents[2] / "prompts" / "default.md"
        return repo_prompt.read_text(encoding="utf-8")


def ensure_user_files() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")
    if not PROMPT_PATH.exists():
        PROMPT_PATH.write_text(_bundled_prompt_text(), encoding="utf-8")


def load_config(path: Path | None = None) -> Config:
    target = path or CONFIG_PATH
    if not target.exists():
        ensure_user_files()
    with target.open("rb") as f:
        data = tomllib.load(f)
    return Config.model_validate(data)


def _toml_value(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if v is None:
        return '""'
    s = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def save_config(cfg: Config, path: Path | None = None) -> None:
    target = path or CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"hotkey = {_toml_value(cfg.hotkey)}",
        f"hotkey_mode = {_toml_value(cfg.hotkey_mode)}",
        f"min_record_ms = {cfg.min_record_ms}",
        f"sound_feedback = {_toml_value(cfg.sound_feedback)}",
        f"show_overlay = {_toml_value(cfg.show_overlay)}",
        f"ui_language = {_toml_value(cfg.ui_language)}",
        "",
        "[whisper]",
        f"model = {_toml_value(cfg.whisper.model)}",
        f"language = {_toml_value(cfg.whisper.language)}",
        f"compute_type = {_toml_value(cfg.whisper.compute_type)}",
        f"device = {_toml_value(cfg.whisper.device)}",
        "",
        "[ollama]",
        f"enabled = {_toml_value(cfg.ollama.enabled)}",
        f"url = {_toml_value(cfg.ollama.url)}",
        f"model = {_toml_value(cfg.ollama.model)}",
        f"timeout_s = {cfg.ollama.timeout_s}",
        f"temperature = {cfg.ollama.temperature}",
        "",
        "[paste]",
        f"auto_paste = {_toml_value(cfg.paste.auto_paste)}",
        f"paste_delay_ms = {cfg.paste.paste_delay_ms}",
        f"restore_clipboard = {_toml_value(cfg.paste.restore_clipboard)}",
        "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")


def save_prompt(text: str, path: Path | None = None) -> None:
    target = path or PROMPT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
