"""
Small shared helpers used by both api.py (the on-screen explanation) and
pdf_export.py (the downloaded PDF), so both stay consistent instead of
drifting apart.

Why this exists: asking the LLM to wrap medicine names in **bold**
markdown and trusting that formatting to survive a translation pass
turned out to be unreliable - Sarvam is a translation model, not a
markdown-aware one, and doesn't consistently preserve ** markers,
especially across multiple paragraphs. Bolding the name deterministically
in code, after translation, guarantees it's always correct regardless of
what the LLM or translator did with formatting.
"""
import re

import sarvam_translator


def translate_medicine_fields(medicines: list[dict], language_code: str) -> list[dict]:
    """Returns a copy of medicines with dosage/frequency/duration/
    instructions translated into the target language. The name itself is
    deliberately left untranslated - it's what's printed on the actual
    pill box or strip, and translating it would make it harder, not
    easier, to match."""
    translated = []
    for m in medicines:
        copy = dict(m)
        for field in ("dosage", "frequency", "duration", "instructions"):
            if copy.get(field):
                copy[field] = sarvam_translator.translate(copy[field], language_code)
        translated.append(copy)
    return translated


def bold_medicine_names(text: str, medicine_names: list[str]) -> str:
    """Guarantees each medicine name appears in **bold** markdown in the
    explanation text, regardless of whether the LLM/translator already
    formatted it that way. Strips any existing (possibly malformed or
    partial) bold markers around the name first, then re-applies bolding
    cleanly and consistently everywhere the name appears."""
    for name in medicine_names:
        escaped = re.escape(name)
        # Remove any existing bold markers directly around this name
        # (handles cases where translation left a stray single "*" or
        # a mismatched marker behind)
        text = re.sub(rf"\*{{1,2}}\s*({escaped})\s*\*{{1,2}}", r"\1", text)
        # Now wrap every occurrence in clean, matching ** markers
        text = re.sub(rf"(?<!\*)({escaped})(?!\*)", r"**\1**", text)
    return text
