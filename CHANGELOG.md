# Changelog

## v0.2.9 — 2026-05-09

- **Hard guard against the main window auto-opening**. The expected behaviour is: dock icon stays visible while voxless writes, the text gets pasted into the focused input, and the main window does NOT pop up. v0.2.9 enforces that with a hard authorization flag — `MainWindow.show()` and `MainWindow.setVisible(True)` are overridden to silently ignore any call that wasn't explicitly authorized via `show_authorized()`. The only call sites that authorize are: tray-icon click and first-run welcome. Anything else (Qt's own auto-show, NSApplicationDelegate's `applicationShouldHandleReopen`, focus events, paste-time activation cascades) gets dropped on the floor.
- closeEvent resets the authorization flag, so closing the window via the X button means the next show requires re-authorization.

## v0.2.8 — 2026-05-09

- **Dock icon back**. Reverted v0.2.6's accessory-app switch (`LSUIElement: True` / `setActivationPolicy(.accessory)`) — voxless now shows in the Dock and Cmd-Tab again. The hotkey listener was also flaky in accessory mode for some users; reverting fixes both.
- The `force-hide on idle` defense from v0.2.5 stays in place, so the main window still shouldn't auto-open during recording.

## v0.2.7 — 2026-05-09

- **Cleaner feedback sounds**. Replaced the gluey "bubble plop" with crisp percussive clicks: pure sine + a hint of 2nd harmonic, tight attack-decay envelope. Start at 720 Hz (60 ms), stop at 540 Hz (70 ms) — feels like a real on/off, not a kid's app.

## v0.2.6 — 2026-05-09

Architectural fix for the recurring "voxless takes focus / opens its window" bug.

- **voxless is now an accessory app on macOS** (`NSApplicationActivationPolicyAccessory` set at startup, `LSUIElement: True` in Info.plist). No dock icon, no Cmd-Tab listing — the app lives in the menu-bar tray, exactly like Linear / Raycast / Slack do for their tray UIs. The overlay can no longer drag the main window into focus, because there's no "main app" to activate. The widget is fully decoupled from the main window.
- The main window remains reachable from the tray icon's menu, and behaves like a normal window when you bring it up — but it never auto-shows again.

## v0.2.5 — 2026-05-08

- **Two-step paste**: activate target app via `osascript` (no permissions required) → wait 180 ms → send Cmd+V via pynput (which already holds Accessibility). Fixes the silent paste-failure caused by `osascript`'s `System Events keystroke` requiring its own Accessibility grant we can't ensure for end users.
- **Force-hide main window when state returns to idle**, *unless* the user explicitly opened the window from the tray. Even if voxless's main window somehow snuck visible during recording, it gets hidden as soon as we go back to idle.

## v0.2.4 — 2026-05-08

Decoupled paste from voxless's own focus state.

- **Direct paste via AppleScript / SendInput**. We capture the foreground app's *name* (or HWND on Windows) when you press the hotkey. After cleanup, we put the cleaned text on the clipboard and dispatch `Cmd+V` (or `Ctrl+V`) **directly at that app** via `osascript "tell application X to activate" + System Events keystroke` (macOS) or `SetForegroundWindow + keybd_event` (Windows). voxless never touches its own focus.
- **No more `NSApp.hide()`**. The previous "deactivate self" call was leaving voxless in a half-hidden state where the tray icon couldn't bring the window back. With direct-paste, we don't need to hide ourselves at all.
- **No more "main window opens after transcription"**. We never call `activate` on a captured pid (which used to occasionally re-summon our own window) and we no longer need to hide+unhide.

## v0.2.3 — 2026-05-08

Two critical fixes from user testing.

- **No more "stuck in REC"**. The release-event handler is now wrapped in a `try / finally` that guarantees the state machine returns to `idle` no matter what fails inside (Whisper hang, Ollama timeout, paste error). Recorder.start() also force-cleans any leftover stream from a prior aborted session, so a second hotkey press always opens a clean input.
- **Voxless never re-opens its window after transcription**. Replaced the capture-and-restore-frontmost dance with `frontmost.deactivate_self()`: if voxless is in the foreground at paste-time, we hide ourselves with `NSApplication.hide_(None)` (macOS) / `ShowWindow(SW_MINIMIZE)` (Windows). The OS hands focus back to whatever app the user was previously in, and `Cmd+V` / `Ctrl+V` lands there. We never call `activate` on a captured PID — that was the path that occasionally re-summoned our own main window.

## v0.2.2 — 2026-05-08

- **Spanish / English UI**. New `i18n` module with the full string catalog. New row in **General** to switch language; saved to config (`ui_language`). The whole app — sidebar, page headers, settings rows, button labels, status text, toasts, permission badges, hero copy — flips on save (next launch is fully bilingual; the current session updates everything reachable from the toast).
- **Stronger paste-target guard**. `frontmost.get_frontmost()` now actively rejects voxless's own pid/bundle, so we can never accidentally capture-then-restore *ourselves* (which had been re-opening the main window after transcription). Combined with v0.2.1's "only restore if voxless is frontmost" gate, paste reliably lands at the cursor position the user clicked.

## v0.2.1 — 2026-05-08

- **Paste lands at the cursor**, not at the end of a wrong window. v0.1.10 always restored the captured frontmost app before pasting, which on macOS sometimes activated a different window of that app and dropped the cursor at the wrong place. v0.2.1 only restores when voxless itself is currently the foreground app — otherwise it leaves focus exactly where the user left it (cursor inside the input they clicked into).
- Increased restore-then-paste delay to 150 ms so macOS / Windows have time to settle the activation before Cmd+V / Ctrl+V fires.
- New `frontmost.is_voxless_frontmost()` helper used to gate the restore.

## v0.2.0 — 2026-05-08

Nothing-inspired full UI redesign.

- **New design language**: pure black + pure white + Nothing red `#ff3636` accent. Sharp 2px corners (no rounded cards). Mono LED-feel typography across the app — Fraunces/Iowan Old Style replaced by SF Mono / Menlo at 800 weight for display impact.
- **Industrial numbering** in nav and rows: `001 INDEX · 002 GENERAL · 003 PERMS · 004 WHISPER · 005 OLLAMA · 006 PROMPT · 007 LEDGER`. Two-letter status codes: `READY · REC · WRITE · ERROR`.
- **Glyph-pixel VU meter**. Five-row by nine-column LED grid (Nothing's signature dot-matrix), peak rows light red.
- **Display title**: `DICTATE / IN SILENCE.` set in 56px bold mono. Hotkey shown as huge mono `⌥R · ⇧L · F5` etc, with `◉ HOTKEY` and `◉ MODE` micro-labels.
- **Permission status badges** as bordered LED chips: `● GRANTED` (green), `○ MISSING` (red), `— UNKNOWN` (grey).
- **Floating overlay redesigned**: pure black pill, square LED dot, 5×9 pixel meter, monospace `REC / WRITE / READY` labels.
- **Toast redesigned**: square corners, colored stripe, mono uppercase label + message.
- **Buttons** stay sharp-corner inline-styled (immune to QSS cascade quirks). Primary = white-on-black at rest, red on hover. Default = transparent with `#2a2a2a` border, surface fill on hover.

## v0.1.10 — 2026-05-08

Critical paste-target fix.

- **No auto-show on every launch**. The main window now opens only on first run (when the config file doesn't exist yet). After that voxless lives in the tray + overlay, so it never grabs focus from the app you're dictating into. The window opens on demand from the tray icon.
- **Capture & restore frontmost app**. Right when you press the hotkey, voxless records which app was foremost (NSWorkspace on macOS, GetForegroundWindow on Windows). Right before pasting, it activates that app again, then sends Cmd+V / Ctrl+V. This guarantees the cleaned text lands where you wanted it, even if the overlay or our tray briefly competed for focus.

## v0.1.9 — 2026-05-08

- **AI actions on history items**. Right-click any transcription (or click "ACCIONES IA" with a row selected) for: Mejorar redacción, Resumir, Tono formal, Tono casual, Traducir a inglés / a español. Each runs through Ollama with a dedicated system prompt and copies the result to your clipboard with a toast confirmation.
- **No more "Bien, aquí tienes…" preamble**. Default cleanup prompt rewritten with explicit forbidden-openings list + extra few-shot examples. Added a regex-based post-processor in OllamaClient that strips conversational preamble + wrapping quotes even when the model defies instructions.
- **Bubble-plop feedback sounds**. Synthesized in pure numpy (no bundled assets) — a wet rising plop on start (180 → 320 Hz, 14 ms attack, exponential decay) and a softer falling plop on stop (320 → 160 Hz). Plays through the default audio output, non-blocking. Toggle in **General → Sonido al grabar**.
- **Floating recorder overlay**. A discreet pill anchored to the bottom-center of the primary screen shows live state (REC dot pulse + 7-bar mini meter while recording, "WRITING" while Ollama is processing). Frameless, always-on-top, doesn't take focus, fades in/out. Toggle in **General → Widget flotante**.
- **Tighter Whisper transcription**. Wider beam (8), best-of (5), multi-temperature fallback `[0, 0.2, 0.4, 0.6, 0.8]`, `condition_on_previous_text=False`, generous VAD padding (`min_silence_duration_ms=500`, `speech_pad_ms=400`), and a small Spanish vocabulary `initial_prompt` to anchor common dictation phrases. Should reduce both hallucinations and word loss.
- **Inline-styled buttons across the UI** — primary buttons render as solid black with white text everywhere (Guardar cambios / Guardar prompt / Solicitar acceso); secondaries as paper with dark text and a real border. Cascade-proof.
- **Sharper app icon** with a thicker italic v + amber dash (regenerated icns/ico).

## v0.1.8 — 2026-05-08

- **Truly bulletproof "Guardar cambios"**. Inline stylesheets on every primary/default button (overrides app-level QSS, immune to cascade quirks). Pure black background + pure white text on the primary action — no more invisible labels.
- **Bolder app icon**. Italic Georgia "v" rendered at 780 weight with thicker amber dash + corner dot. Recognizable down to 16×16 in the dock and taskbar.
- **Helpers**: `primary_btn()` / `default_btn()` factories so future buttons inherit the right look without re-discovering Qt's button quirks.

## v0.1.7 — 2026-05-08

- **Bulletproof button styles**. v0.1.6 used `background:` (shorthand) and a universal `* { color }` rule that Qt sometimes resolved against more-specific selectors, leaving Primary buttons with the wrong text color. Now every button state explicitly sets `background-color` AND `color` (resting / hover / pressed / disabled). Save buttons are clearly readable on both light and dark.
- **Permisos page on Windows**. Added a real microphone-access probe (opens a 100 ms input stream — if Windows privacy is blocking it raises immediately) and a Hotkey row that links to Windows Defender settings + suggests "Run as administrator" for the case where AV blocks keyboard hooks.
- **Better description copy** for Windows microphone (mentions both privacy toggles users need to flip).
- Version footer in sidebar bumped.

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
