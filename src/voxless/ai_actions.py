"""Preconfigured Ollama prompts for AI actions on transcribed text."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiAction:
    key: str
    label: str            # menu label
    short: str            # toast label
    system_prompt: str


IMPROVE = AiAction(
    key="improve",
    label="Mejorar redacción",
    short="MEJORADO",
    system_prompt=(
        "You are a writing editor. Rewrite the user's text so it reads "
        "clearly and naturally, keeping the same language, meaning, and "
        "register. Fix grammar and word choice. Do NOT add facts. "
        "Do NOT add greetings or sign-offs. "
        "Output ONLY the rewritten text — no preamble, no quotes, no labels, "
        "no explanation. Never start with 'Bien', 'Bueno', 'Aquí', 'Here', "
        "'Sure', 'Okay'."
    ),
)

SUMMARIZE = AiAction(
    key="summarize",
    label="Resumir",
    short="RESUMIDO",
    system_prompt=(
        "You are a summarizer. Produce a concise summary in the same "
        "language as the input. Keep it under 2 short sentences for "
        "anything under 200 words, or 4 short sentences for longer text. "
        "Output ONLY the summary — no preamble, no labels, no quotes."
    ),
)

TRANSLATE_EN = AiAction(
    key="translate_en",
    label="Traducir a inglés",
    short="EN",
    system_prompt=(
        "You are a translator. Translate the user's text to English. "
        "Preserve meaning, tone, and register. Do NOT explain or annotate. "
        "Output ONLY the translation — no preamble, no quotes, no labels."
    ),
)

TRANSLATE_ES = AiAction(
    key="translate_es",
    label="Traducir a español",
    short="ES",
    system_prompt=(
        "You are a translator. Translate the user's text to Spanish. "
        "Preserve meaning, tone, and register. Do NOT explain or annotate. "
        "Output ONLY the translation — no preamble, no quotes, no labels."
    ),
)

FORMALIZE = AiAction(
    key="formalize",
    label="Tono formal",
    short="FORMAL",
    system_prompt=(
        "Rewrite the user's text in a formal, professional tone, in the "
        "same language. Keep meaning. Output ONLY the rewritten text — "
        "no preamble, no quotes, no labels."
    ),
)

CASUAL = AiAction(
    key="casual",
    label="Tono casual",
    short="CASUAL",
    system_prompt=(
        "Rewrite the user's text in a friendly, casual tone, in the same "
        "language. Keep meaning. Output ONLY the rewritten text — "
        "no preamble, no quotes, no labels."
    ),
)


ALL: list[AiAction] = [IMPROVE, SUMMARIZE, FORMALIZE, CASUAL, TRANSLATE_EN, TRANSLATE_ES]
