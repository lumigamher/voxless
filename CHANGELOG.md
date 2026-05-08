# Changelog

## v0.1.0 — 2026-05-08

Initial release.

- Push-to-talk dictation pipeline (faster-whisper + Ollama + paste).
- PySide6 main window with sidebar (Inicio, Whisper, Ollama, Prompt, Historial).
- Live waveform feedback during recording.
- Cross-platform tray (Qt `QSystemTrayIcon`) — works on macOS and Windows.
- Configurable hotkey, supports modifier combos.
- Editable cleanup prompt per-user (`~/.config/voxless/prompt.md`).
- macOS-native style; Windows themed to look macOS-like.
- Logging to `~/Library/Logs/voxless/voxless.log` (mac) / `%APPDATA%\voxless\Logs\` (win).
