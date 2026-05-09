"""Tiny in-memory i18n. UI strings live in TRANSLATIONS keyed by code, then
by string-id. ``t(key)`` reads the current language; ``set_lang(code)``
swaps it on the fly (callers re-render).
"""

from __future__ import annotations

from typing import Literal

Lang = Literal["es", "en"]

TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        # ── sidebar ───────────────────────────────────────────────
        "side.tagline": "◉ DICTAR · LOCAL",
        "side.section": "ÍNDICE",
        "side.versionsuffix": "LOCAL · 16K",
        "nav.home": "ÍNDICE",
        "nav.general": "GENERAL",
        "nav.permissions": "PERMISOS",
        "nav.whisper": "WHISPER",
        "nav.ollama": "OLLAMA",
        "nav.prompt": "PROMPT",
        "nav.history": "HISTORIAL",

        # ── hero ──────────────────────────────────────────────────
        "hero.ready_idle": "LISTO · INACTIVO",
        "hero.rec_live": "REC · EN VIVO",
        "hero.processing": "ESCRIBE · WHISPER → OLLAMA",
        "hero.title": "DICTA\nEN SILENCIO.",
        "hero.lead": (
            "Mantén tu tecla · habla · suelta. "
            "voxless transcribe localmente con Whisper, pule con Ollama, "
            "y escribe en la app que tengas enfocada. "
            "Privado. Rápido. Offline."
        ),
        "hero.hotkey": "◉ TECLA",
        "hero.mode": "◉ MODO",
        "hero.mode.hold": "MANTENER",
        "hero.mode.toggle": "TAP-ACTIVAR",
        "hero.level": "◉ NIVEL",
        "hero.last.waiting": "◉ ÚLTIMO · ESPERANDO",
        "hero.last.template": "◉ ÚLTIMO · {time}",
        "hero.last.empty": "— Aún no hay transcripciones. Mantén tu tecla para empezar.",

        # ── pages ─────────────────────────────────────────────────
        "page.general.eyebrow": "001 · CONTROL",
        "page.general.title": "GENERAL",
        "page.general.sub": "Tecla, modo de activación y comportamiento de grabación.",

        "page.permissions.eyebrow": "002 · ACCESO",
        "page.permissions.title": "PERMISOS",
        "page.permissions.sub": "Necesarios para escuchar tu tecla y usar el micrófono.",

        "page.whisper.eyebrow": "003 · TRANSCRIPCIÓN",
        "page.whisper.title": "WHISPER",
        "page.whisper.sub": "Reconocimiento local de voz vía faster-whisper / CTranslate2.",

        "page.ollama.eyebrow": "004 · REDACCIÓN",
        "page.ollama.title": "OLLAMA",
        "page.ollama.sub": "LLM local que pule el texto transcrito.",

        "page.prompt.eyebrow": "005 · INSTRUCCIONES",
        "page.prompt.title": "PROMPT",
        "page.prompt.sub": "Prompt enviado a Ollama. Reglas de estilo + ejemplos few-shot.",

        "page.history.eyebrow": "006 · REGISTRO",
        "page.history.title": "HISTORIAL",
        "page.history.sub": "Últimas 100 transcripciones. Doble click copia · click derecho para IA.",

        # ── general rows ──────────────────────────────────────────
        "general.hotkey.title": "TECLA",
        "general.hotkey.desc": "Click y presiona la tecla — o combinación — que quieras usar.",
        "general.activation.title": "ACTIVACIÓN",
        "general.activation.desc": "Cómo se controla la grabación con la tecla.",
        "general.activation.hold": "Mantener · push-to-talk",
        "general.activation.toggle": "Tocar para iniciar · tocar para parar",
        "general.minduration.title": "DURACIÓN MÍN",
        "general.minduration.desc": "Las grabaciones más cortas se ignoran.",
        "general.sound.title": "SONIDO",
        "general.sound.desc": "Click sutil al iniciar y al detener.",
        "general.overlay.title": "OVERLAY",
        "general.overlay.desc": "Indicador glyph flotante abajo en la pantalla.",
        "general.lang.title": "IDIOMA",
        "general.lang.desc": "Idioma de la interfaz.",
        "general.lang.es": "Español",
        "general.lang.en": "English",
        "general.checkbox.enabled": "ACTIVADO",

        # ── whisper rows ──────────────────────────────────────────
        "whisper.model.title": "MODELO",
        "whisper.model.desc": "Más grande = más exacto, más lento. small es el sweet spot.",
        "whisper.lang.title": "IDIOMA",
        "whisper.lang.desc": "Vacío para auto-detectar.",
        "whisper.lang.placeholder": "auto · es · en · fr …",
        "whisper.precision.title": "PRECISIÓN",
        "whisper.precision.desc": "int8 va rápido y exacto. float16/32 piden GPU.",
        "whisper.device.title": "DEVICE",
        "whisper.device.desc": "auto detecta GPU (Metal/CUDA) si está disponible.",

        # ── ollama rows ───────────────────────────────────────────
        "ollama.enabled.title": "PULIR",
        "ollama.enabled.desc": "Desactiva para pegar el texto crudo de Whisper.",
        "ollama.url.title": "URL",
        "ollama.url.desc": "Endpoint del servidor Ollama.",
        "ollama.model.title": "MODELO",
        "ollama.model.desc": "Cualquier modelo que tengas con `ollama pull`.",
        "ollama.timeout.title": "TIMEOUT",
        "ollama.timeout.desc": "Si Ollama tarda más, voxless pega texto crudo.",
        "ollama.temperature.title": "TEMPERATURA",
        "ollama.temperature.desc": "0 = literal · 1 = más libre.",

        # ── buttons ───────────────────────────────────────────────
        "btn.save": "Guardar",
        "btn.save_prompt": "Guardar Prompt",
        "btn.copy": "Copiar",
        "btn.clear": "Limpiar",
        "btn.ai_actions": "Acciones IA",
        "btn.verify": "Verificar",
        "btn.settings": "Ajustes",
        "btn.request_access": "Solicitar Acceso",

        # ── permissions ───────────────────────────────────────────
        "perm.granted": "● CONCEDIDO",
        "perm.missing": "○ FALTA",
        "perm.unknown": "— DESCONOCIDO",
        "perm.tip": (
            "<b>NOTA</b> — si System Settings no deja seleccionar voxless, "
            "arrastra <code>/Applications/voxless.app</code> desde Finder al panel. "
            "Al conceder un permiso, vuelve y pulsa <i>Verificar</i>."
        ),

        # ── toasts ────────────────────────────────────────────────
        "toast.saved.config": "GUARDADO · CONFIG APLICADA",
        "toast.saved.prompt": "GUARDADO · PROMPT APLICADO",
        "toast.save_failed": "ERROR · {error}",
    },
    "en": {
        "side.tagline": "◉ DICTATE · LOCAL",
        "side.section": "INDEX",
        "side.versionsuffix": "LOCAL · 16K",
        "nav.home": "INDEX",
        "nav.general": "GENERAL",
        "nav.permissions": "PERMS",
        "nav.whisper": "WHISPER",
        "nav.ollama": "OLLAMA",
        "nav.prompt": "PROMPT",
        "nav.history": "LEDGER",

        "hero.ready_idle": "READY · IDLE",
        "hero.rec_live": "REC · LIVE",
        "hero.processing": "WRITE · WHISPER → OLLAMA",
        "hero.title": "DICTATE\nIN SILENCE.",
        "hero.lead": (
            "Hold your hotkey · speak · release. "
            "voxless transcribes locally with Whisper, polishes with Ollama, "
            "and types into the focused app. "
            "Private. Fast. Offline."
        ),
        "hero.hotkey": "◉ HOTKEY",
        "hero.mode": "◉ MODE",
        "hero.mode.hold": "PUSH-TO-TALK",
        "hero.mode.toggle": "TAP-TOGGLE",
        "hero.level": "◉ LEVEL",
        "hero.last.waiting": "◉ LAST · WAITING",
        "hero.last.template": "◉ LAST · {time}",
        "hero.last.empty": "— No transcriptions yet. Hold your hotkey to begin.",

        "page.general.eyebrow": "001 · CONTROL",
        "page.general.title": "GENERAL",
        "page.general.sub": "Hotkey, activation mode and recording behaviour.",

        "page.permissions.eyebrow": "002 · ACCESS",
        "page.permissions.title": "PERMS",
        "page.permissions.sub": "Required for global hotkey listening and microphone access.",

        "page.whisper.eyebrow": "003 · TRANSCRIPTION",
        "page.whisper.title": "WHISPER",
        "page.whisper.sub": "Local speech-to-text via faster-whisper / CTranslate2.",

        "page.ollama.eyebrow": "004 · COPYDESK",
        "page.ollama.title": "OLLAMA",
        "page.ollama.sub": "Local LLM that polishes the transcribed text.",

        "page.prompt.eyebrow": "005 · INSTRUCTIONS",
        "page.prompt.title": "PROMPT",
        "page.prompt.sub": "System prompt sent to Ollama. Style rules + few-shot examples.",

        "page.history.eyebrow": "006 · LEDGER",
        "page.history.title": "HISTORY",
        "page.history.sub": "Last 100 transcriptions. Double-click to copy · right-click for AI.",

        "general.hotkey.title": "HOTKEY",
        "general.hotkey.desc": "Click and press the key — or combination — you want to use.",
        "general.activation.title": "ACTIVATION",
        "general.activation.desc": "How the hotkey controls the recording.",
        "general.activation.hold": "Hold · push-to-talk",
        "general.activation.toggle": "Tap to start · tap to stop",
        "general.minduration.title": "MIN DURATION",
        "general.minduration.desc": "Recordings shorter than this are ignored.",
        "general.sound.title": "SOUND",
        "general.sound.desc": "Subtle bubble click on start and stop.",
        "general.overlay.title": "OVERLAY",
        "general.overlay.desc": "Floating glyph indicator at the bottom of the screen.",
        "general.lang.title": "LANGUAGE",
        "general.lang.desc": "Interface language.",
        "general.lang.es": "Español",
        "general.lang.en": "English",
        "general.checkbox.enabled": "ENABLED",

        "whisper.model.title": "MODEL",
        "whisper.model.desc": "Larger = more accurate, slower. small is the sweet spot.",
        "whisper.lang.title": "LANGUAGE",
        "whisper.lang.desc": "Empty for auto-detect.",
        "whisper.lang.placeholder": "auto · es · en · fr …",
        "whisper.precision.title": "PRECISION",
        "whisper.precision.desc": "int8 is fast and accurate. float16/32 require GPU.",
        "whisper.device.title": "DEVICE",
        "whisper.device.desc": "auto detects GPU (Metal / CUDA) when available.",

        "ollama.enabled.title": "POLISH",
        "ollama.enabled.desc": "Disable to paste raw Whisper output.",
        "ollama.url.title": "URL",
        "ollama.url.desc": "Ollama server endpoint.",
        "ollama.model.title": "MODEL",
        "ollama.model.desc": "Any model you've pulled with `ollama pull`.",
        "ollama.timeout.title": "TIMEOUT",
        "ollama.timeout.desc": "If Ollama exceeds this, voxless pastes raw text.",
        "ollama.temperature.title": "TEMPERATURE",
        "ollama.temperature.desc": "0 = literal · 1 = freer.",

        "btn.save": "Save",
        "btn.save_prompt": "Save Prompt",
        "btn.copy": "Copy",
        "btn.clear": "Clear",
        "btn.ai_actions": "AI Actions",
        "btn.verify": "Verify",
        "btn.settings": "Settings",
        "btn.request_access": "Request Access",

        "perm.granted": "● GRANTED",
        "perm.missing": "○ MISSING",
        "perm.unknown": "— UNKNOWN",
        "perm.tip": (
            "<b>NOTE</b> — if System Settings won't let you select voxless, "
            "drag <code>/Applications/voxless.app</code> from Finder onto the "
            "panel. After granting, come back and press <i>Verify</i>."
        ),

        "toast.saved.config": "SAVED · CONFIG APPLIED",
        "toast.saved.prompt": "SAVED · PROMPT APPLIED",
        "toast.save_failed": "SAVE FAILED · {error}",
    },
}

_current: str = "es"


def set_lang(code: str) -> None:
    global _current
    if code in TRANSLATIONS:
        _current = code


def lang() -> str:
    return _current


def t(key: str, **kwargs: object) -> str:
    bundle = TRANSLATIONS.get(_current, TRANSLATIONS["en"])
    raw = bundle.get(key) or TRANSLATIONS["en"].get(key) or key
    if kwargs:
        try:
            return raw.format(**kwargs)
        except Exception:
            return raw
    return raw
