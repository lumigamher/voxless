# Changelog

## v0.1.2 — 2026-05-08

- **New page: Permisos**. Detects Accessibility, Input Monitoring, and Microphone status (granted / falta / desconocido) and exposes one-click buttons to open the matching System Settings pane. Refreshes automatically when the page is shown and on demand.
- **New page: General**. Edit hotkey, hotkey mode (push-to-talk vs tap-toggle), minimum recording duration, and sound feedback from the UI.
- **Configurable workflow**: `hotkey_mode = "hold"` (default — keep the key pressed) or `"toggle"` (tap once to start, tap again to stop).
- **Restored dock icon** — `LSUIElement: False`. voxless behaves like a regular Mac app again, while still keeping the tray icon and single-instance lock from v0.1.1.

## v0.1.1 — 2026-05-08

- **Single-instance lock** via `QLocalServer`. A second launch now brings the existing window to front and exits, instead of spawning a duplicate.
- **Hide dock icon on macOS** (`LSUIElement: True`). voxless now lives only in the system tray, like Typeless.
- **Prohibit multiple `.app` instances** (`LSMultipleInstancesProhibited: True`).
- **Defensive config reload**. Saving settings no longer rebinds the global hotkey (or recreates Whisper / Ollama / Paster) unless those specific values actually changed. Fixes app self-restarting after Save.

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
