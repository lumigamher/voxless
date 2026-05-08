# voxless

Local push-to-talk dictation. Hold a hotkey, speak, release — voxless transcribes with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) locally, cleans the text with [Ollama](https://ollama.com), and pastes it into whatever app has focus.

**100% local. No cloud, no telemetry.** Works on macOS and Windows.

![status](https://img.shields.io/badge/status-alpha-orange)
![platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Windows-blue)
![python](https://img.shields.io/badge/python-3.11%2B-blue)

## Features

- Push-to-talk hotkey (default: right Option / right Alt)
- Real-time waveform feedback in the main window
- Live transcription history per session
- Editable LLM cleanup prompt
- Tray icon with quick access to config, prompt, and logs
- Cross-platform native UI (Qt — macOS uses native style, Windows is themed macOS-like)

## Install (end-user)

Download a pre-built release for your OS from the [Releases page](https://github.com/lumigamher/voxless/releases):

- **macOS (Apple Silicon)**: `voxless-macos-arm64.dmg` — drag `voxless.app` to Applications.
- **Windows (x64)**: `voxless-windows-x64.zip` — extract anywhere, run `voxless.exe`.

### macOS: "no pudo validar la seguridad" / "cannot be opened because Apple cannot check it for malicious software"

The binary is ad-hoc signed but **not** notarized (Apple Developer ID + notarization costs $99/yr; PRs welcome). Browsers add a quarantine flag on download that Gatekeeper blocks. Strip it once:

```bash
xattr -d com.apple.quarantine ~/Downloads/voxless-macos-arm64.dmg
# install the .app, then if it still gets blocked:
xattr -cr /Applications/voxless.app
```

Or right-click the DMG (or app) → **Open** — Gatekeeper shows an extra "Open" button that double-click hides.

You also need [Ollama](https://ollama.com) running locally with at least one model:

```bash
ollama pull gemma3:1b
```

### macOS permissions

The first run will prompt you for these (or approve manually in **System Settings → Privacy & Security**):

- **Microphone** — to record audio
- **Accessibility** — for the global hotkey listener and simulated ⌘V
- **Input Monitoring** — for the modifier-key listener

### Windows permissions

Windows Defender SmartScreen may warn the binary is unrecognized — click "More info" → "Run anyway". The app is unsigned (signing certificates cost ~$300/yr; PRs welcome).

## Run from source

```bash
git clone https://github.com/lumigamher/voxless.git
cd voxless
uv sync --no-editable --extra dev
uv run --no-editable voxless
```

Requires [uv](https://github.com/astral-sh/uv) and Python 3.11+.

> The `--no-editable` flag is required because uv 0.11+ marks editable `.pth` files with the macOS `UF_HIDDEN` flag, which Python 3.13+ refuses to load. Non-editable installs copy the package into the venv directly.

First launch generates `~/.config/voxless/config.toml` and `~/.config/voxless/prompt.md` (or `%APPDATA%\voxless\` on Windows — TODO).

## Configuration

Edit `~/.config/voxless/config.toml` or use the in-app settings UI:

```toml
hotkey = "right_option"          # combos like "<ctrl>+<shift>+space" also work

[whisper]
model = "small"                  # tiny | base | small | medium | large-v3
language = "es"                  # null/omitted = auto-detect
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
```

Edit `~/.config/voxless/prompt.md` (or use the in-app **Prompt** tab) to change how Ollama cleans your dictation. The bundled prompt uses a few-shot template that works even with very small models. For better cleanup quality, try `llama3.1:8b` (~5 GB).

## Build from source

```bash
uv pip install pyinstaller
uv run pyinstaller voxless.spec --noconfirm --clean
```

Output appears in `dist/voxless.app` (macOS) or `dist/voxless/` (Windows).

## Tests

```bash
uv run pytest
```

## Logs

- macOS: `~/Library/Logs/voxless/voxless.log`
- Windows: `%APPDATA%\voxless\Logs\voxless.log`

Both rotate at 10 MB.

## Stack

| Layer        | Tech                                    |
| ------------ | --------------------------------------- |
| Audio capture | `sounddevice` (PortAudio)              |
| STT          | `faster-whisper` (CTranslate2)          |
| LLM cleanup  | Ollama HTTP `/api/chat`                 |
| Hotkey       | `pynput`                                |
| Paste        | `pyperclip` + `pynput`                  |
| UI           | PySide6 (Qt) + system tray              |
| Packaging    | PyInstaller                             |
| CI           | GitHub Actions (macOS + Windows runners) |

## License

MIT
