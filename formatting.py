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
from concurrent.futures import ThreadPoolExecutor

import sarvam_translator

_TRANSLATABLE_FIELDS = ("dosage", "frequency", "duration", "instructions")


def translate_medicine_fields(medicines: list[dict], language_code: str) -> list[dict]:
    """Returns a copy of medicines with dosage/frequency/duration/
    instructions translated into the target language, PLUS a new
    "name_local" field - the medicine name transliterated (not
    translated) into the target script, e.g. "Nilhist-M" ->
    "निलहिस्ट-एम". The original "name" field is left untouched - it's
    what's printed on the actual pill box or strip, and translating its
    *meaning* would be actively wrong (brand names aren't real words),
    while showing ONLY the transliterated form would make it harder to
    match against the physical packaging. Showing both is the point.

    Every field across every medicine is an independent Sarvam call, so
    they all run in parallel rather than one at a time - for a
    prescription with several medicines this was the main source of
    slowness (10+ sequential network round-trips otherwise)."""
    translated = [dict(m) for m in medicines]

    # (index into `translated`, field name) -> the translate/transliterate
    # call to make, so results can be written back to the right spot
    # once every call finishes, regardless of the order they complete in.
    jobs: list[tuple[int, str, callable]] = []
    for i, m in enumerate(translated):
        for field in _TRANSLATABLE_FIELDS:
            if m.get(field):
                jobs.append((i, field, lambda v=m[field]: sarvam_translator.translate(v, language_code)))
        jobs.append((i, "name_local", lambda v=m["name"]: sarvam_translator.transliterate(v, language_code)))

    with ThreadPoolExecutor(max_workers=min(16, len(jobs) or 1)) as pool:
        futures = {pool.submit(fn): (i, field) for i, field, fn in jobs}
        for future in futures:
            i, field = futures[future]
            translated[i][field] = future.result()

    return translated


def apply_transliterated_names(text: str, medicines: list[dict]) -> str:
    """In the (already translated) explanation text, swaps each
    occurrence of a medicine's English name for its transliterated form
    in bold, e.g. "Nilhist-M is used for..." becomes
    "**निलहिस्ट-एम** is used for...". In practice Sarvam's translation
    pass usually leaves brand names in Latin script untouched inside the
    translated prose, which is what makes this find-and-replace
    reliable - but if a specific name genuinely isn't found (translation
    altered it unpredictably), that medicine is left as a plain bold
    English name instead, via the existing bold_medicine_names fallback,
    rather than silently dropping it."""
    still_english = []
    for m in medicines:
        name, name_local = m["name"], m.get("name_local", m["name"])
        if name == name_local:
            still_english.append(name)
            continue
        escaped = re.escape(name)
        if re.search(escaped, text):
            text = re.sub(rf"\*{{1,2}}\s*({escaped})\s*\*{{1,2}}", r"\1", text)  # strip any existing bold first
            text = re.sub(escaped, f"**{name_local}**", text, count=1)
        else:
            still_english.append(name)  # name wasn't found verbatim - fall back to bolding the English name

    if still_english:
        text = bold_medicine_names(text, still_english)
    return text


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
