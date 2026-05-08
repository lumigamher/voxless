# Voxless — Local Typeless clone (design)

Date: 2026-05-08
Owner: Luis Miguel
Status: Approved (user authorized full implementation)

## Goal

Clone the core experience of Typeless on macOS, fully local:

- Hold a configurable hotkey → record microphone.
- Release → transcribe locally with Whisper (`faster-whisper`).
- Pass through a local LLM (Ollama) with a configurable prompt for cleanup.
- Auto-paste the cleaned text into whichever app currently has focus.

The only thing the user must configure to get it running is which Ollama model to use (and optionally the system prompt). Everything else has sensible defaults.

## Non-goals

- Cross-platform support (macOS only for v1).
- Cloud transcription / cloud LLMs.
- Multi-user accounts, syncing, telemetry.
- Custom dictionary / vocabulary boosting (future).
- Streaming partial transcriptions while recording (future).

## Stack

| Layer | Choice | Why |
|---|---|---|
| Runtime | Python 3.14 | already on machine, simplest path for native audio + macOS APIs |
| Pkg mgr | `uv` | fast, lockfile, available locally |
| STT | `faster-whisper` (CTranslate2) | local, fast on Apple Silicon, multilingual, model `small` default |
| LLM | Ollama HTTP `/api/chat` via `httpx` | already installed, `gemma3:1b` available |
| Hotkey | `pynput.keyboard.Listener` | low-level, captures modifier keys globally |
| Audio | `sounddevice` (PortAudio) → WAV in-memory | reliable, 16 kHz mono float32 native to Whisper |
| Menu bar | `rumps` | smallest dependency for a real macOS status item |
| Auto-paste | `pyperclip` + `pynput` ⌘V | works in any focused app once Accessibility permission is granted |
| Config | TOML at `~/.config/voxless/config.toml` | user-editable, validated with pydantic |
| Logs | `~/Library/Logs/voxless/voxless.log` | rotating 10 MB |

## Project layout

```
voxless/
├── pyproject.toml
├── README.md
├── prompts/default.md
├── assets/{idle,recording,processing}.png
├── src/voxless/
│   ├── __main__.py        # entry: load config → start app
│   ├── app.py             # orchestrator (state machine)
│   ├── config.py          # pydantic settings + TOML loader
│   ├── hotkey.py          # pynput PTT listener
│   ├── recorder.py        # sounddevice mic → numpy float32
│   ├── transcriber.py     # faster-whisper wrapper (lazy load)
│   ├── llm.py             # Ollama /api/chat client
│   ├── paster.py          # clipboard + simulated ⌘V
│   ├── menubar.py         # rumps app + state-driven icon
│   ├── prompts.py         # load prompt.md (default or user override)
│   └── logging_setup.py
└── tests/
    ├── test_config.py
    ├── test_prompts.py
    ├── test_llm.py        # mock httpx.Client
    └── test_paster.py     # mock pyperclip + pynput
```

Every module under 250 LoC; single responsibility; testable in isolation.

## State machine

```
       press                   stop
IDLE ─────────► RECORDING ───────────► PROCESSING ──► IDLE
  ▲                  │                       │
  │   release        │                       │  error
  └──────────────────┴───────────────────────┘
                                              ▼
                                            ERROR ──(menubar shows ⚠, auto reset 3s)──► IDLE
```

- IDLE: icon ●, listener armed.
- RECORDING: icon 🔴, audio buffering. Min duration guard 250 ms (ignore accidental taps).
- PROCESSING: icon ⏳, transcribe + LLM run on a worker thread. Hotkey is ignored.
- ERROR: icon ⚠, log error, restore IDLE after 3s, expose details in menu.

State is owned by `app.py`; `menubar.py` is a passive view. The hotkey listener never blocks — events are pushed onto a `queue.Queue` consumed by a worker thread.

## Data flow

1. `hotkey.on_press()` → enqueue `START_RECORD`.
2. Worker dispatches: `recorder.start()`, transitions to RECORDING, sets icon.
3. `hotkey.on_release()` → enqueue `STOP_RECORD`.
4. Worker dispatches: `pcm = recorder.stop()`, transitions to PROCESSING.
5. `text_raw = transcriber.transcribe(pcm, language=cfg.whisper_language)`.
6. If `cfg.ollama_enabled`: `text_clean = llm.clean(text_raw, prompt)` else `text_clean = text_raw`.
7. `paster.paste(text_clean)`:
   - Save current clipboard text.
   - `pyperclip.copy(text_clean)`.
   - Send `Cmd+V` via `pynput.keyboard.Controller`.
   - After `paste_delay_ms`, restore previous clipboard (best-effort).
8. Transition back to IDLE; icon ●.

## Config (`~/.config/voxless/config.toml`)

```toml
hotkey = "right_option"          # pynput key name; combos via "<ctrl>+<shift>+v"
min_record_ms = 250
sound_feedback = false

[whisper]
model = "small"                  # tiny | base | small | medium | large-v3
language = "es"                  # null = auto-detect
compute_type = "int8"            # int8 | float16 | float32
device = "auto"                  # auto | cpu

[ollama]
enabled = true
url = "http://localhost:11434"
model = "gemma3:1b"
timeout_s = 30
temperature = 0.2

[paste]
auto_paste = true                # false = leave on clipboard only
paste_delay_ms = 80
restore_clipboard = true
```

First launch generates this file with defaults plus the bundled `prompts/default.md` copied to `~/.config/voxless/prompt.md`.

## Default prompt (Spanish)

The bundled prompt instructs the model to:

- Remove filler words (eh, este, o sea, mmm, …) and false starts.
- Fix obvious recognition errors using context.
- Preserve meaning, tone, register, and language (do not translate).
- Add basic punctuation and capitalization.
- Return ONLY the cleaned text — no preamble, no quotes, no explanation.

The prompt lives at `prompts/default.md` and is overridable per-user.

## Error handling

| Failure | Behavior |
|---|---|
| Mic permission denied | Show alert via `rumps`, link to System Settings, stay IDLE |
| Accessibility permission missing for hotkey/⌘V | Detect at startup, show actionable alert |
| Recording shorter than `min_record_ms` | Cancel silently, return to IDLE |
| Whisper model download interrupted | Retry once; on second fail surface error |
| Ollama unreachable / timeout | Fall back to raw transcription, log a warning, still paste |
| Paste fails (no focused window) | Leave text on clipboard, notify in menubar tooltip |
| Any unhandled exception in worker | Catch, log full traceback, transition to ERROR |

All errors logged with structured context (state, model, duration). No crash takes the menubar app down.

## Threading model

- Main thread: `rumps.App.run()` (must own the macOS run loop).
- Hotkey listener: pynput thread (daemon).
- Worker: 1 dedicated `threading.Thread` consuming a `queue.Queue`. Transcription + LLM + paste all happen here so the UI stays snappy and operations serialize naturally.
- Whisper model: loaded lazily on first transcription, cached on the worker thread.

## Testing

- `test_config.py`: TOML parsing, defaults, validation errors.
- `test_prompts.py`: bundled prompt loads, user override wins.
- `test_llm.py`: `httpx.MockTransport` against Ollama `/api/chat`; timeout fallback path returns raw text.
- `test_paster.py`: monkeypatch `pyperclip` + `pynput` controllers; asserts clipboard set, ⌘V sent, clipboard restored.
- Manual smoke tests (documented in README): mic permission, accessibility permission, end-to-end PTT into TextEdit.

## Packaging / install

- `uv sync` to install deps.
- `uv run voxless` to start (registered as `[project.scripts]`).
- Optional later: `py2app` bundle for double-click `.app`.

## Future (explicitly out of scope for v1)

- Streaming partial transcription while holding hotkey.
- Toggle activation mode (tap-on / tap-off).
- Multiple prompt presets (raw / formal / email / code).
- Per-app prompt overrides.
- Quick clipboard-only mode without Accessibility permission.
- LaunchAgent for auto-start.
- `.app` bundle via `py2app`.
