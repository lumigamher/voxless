# Changelog

## v0.1.6 — 2026-05-08

Studio Print Shop redesign.

- **Aesthetic commit**: voxless as a private printing press for your voice. Editorial × analog studio gear. Cream paper bg, ink near-black, single warm-amber accent (VU-meter peak color). Italic serif for display, monospace for technical readouts.
- **Force Fusion style** at app startup so QSS actually applies — fixes the white-on-white "Guardar cambios" button on macOS.
- **App icon redesigned** as a typographic monogram (italic serif `v.` on a near-black bevel), regenerated `voxless.icns` + `voxless.ico`.
- **New sidebar**: italic serif wordmark `voxless.`, micro tagline, numbered TOC nav (`01 INICIO`, `02 GENERAL`, …), warm-amber selection rule on the left edge.
- **New page header**: section number eyebrow (`§ 02 · WORKSPACE`), italic serif title, italic serif subtitle, hairline below.
- **New hero**: pull-quote-style "Speak. / It prints.", deep-black hotkey panel with mode marker, VU-style waveform with -30 / -20 / -10 / -3 dB tick marks, paper-feel "LAST" panel with serif italic transcription preview.
- **Settings rows**: numbered prefixes, serif title + monospace description, control flush right.
- **Buttons**: monospace ALL CAPS labels, warm-amber primary state, sharp 4px radius.
- **Toast**: inked stripe + monospace label · message slip.

## v0.1.5 — 2026-05-08

- **Refined visual hierarchy**. v0.1.4 had white buttons on white cards; now there are three clear surface levels (page · card · interactive). Default buttons use a tonal `#f4f4f5` fill that reads against both backgrounds. Inputs get stronger borders.
- **State-aware status pill** on the Inicio hero — green when idle, red when grabando, amber when procesando.
- **Soft drop shadow** on the hero card (offset 0/6, blur 28, alpha ~7%) for the right amount of lift without looking 2010.
- **Better hotkey display** — black pill with white text, more "command palette" feel.
- **Polished dark mode** — three-level surface system mirrored, refined hover/selected states for nav, version footer, scrollbar.

## v0.1.4 — 2026-05-08

- **UI redesign — modern + clean**. New palette (off-white surfaces, voxless red accent), refined typography, real Lucide-style SVG icons (no more emoji glyphs in the sidebar), Linear/Raycast-inspired settings rows with hairline dividers instead of boxed cards, hero home screen with a pill status indicator + giant hotkey display.
- **Floating toast notifications**. Saving any settings now shows a slide-in toast confirming the save (or surfacing an error). Auto-dismisses after ~2.4s.
- **New module `icons.py`**: inline SVG icons recolored at render time, packaged as scalable QIcons.
- **Stable code-signing identity** for local builds (`scripts/sign_macos.sh`). macOS TCC stops wiping permissions across rebuilds. Documented in README.

## v0.1.3 — 2026-05-08

- **Hotkey recorder widget**. Click "Tecla" in **General**, then press the key (or combination) you want — voxless captures and stores the right pynput spec automatically. Distinguishes left/right Option / Cmd / Ctrl / Shift via native virtual key codes (Mac and Windows). Esc cancels capture.
- **Smarter Accessibility / Microphone request flow**. Each macOS permission now offers a "Solicitar acceso" button that fires the system prompt directly via `AXIsProcessTrustedWithOptions` (Accessibility) or `AVCaptureDevice.requestAccess` (Microphone) — no more hunting through System Settings. The "Abrir ajustes" deep-link is still available as a fallback.
- **macOS-style UI polish**: SF Pro / system font, sidebar with iconography per nav item, tighter spacing, version string footer, refined hover/selected states for nav, friendlier hotkey display ("⌥ Right" instead of "right_option").

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
