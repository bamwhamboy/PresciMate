"""
Translates the English explanation into the patient's chosen Indian
language with Sarvam's translate API - it's trained specifically on
Indian languages, which tends to read more naturally than asking a
general-purpose model to write directly in a lower-resource language.
"""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from sarvamai import SarvamAI

import config


@lru_cache(maxsize=1)
def _client() -> SarvamAI:
    if not config.SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not set - check your .env file.")
    return SarvamAI(api_subscription_key=config.SARVAM_API_KEY)


def translate(text: str, target_language_code: str, source_language_code: str = "en-IN") -> str:
    if target_language_code == source_language_code:
        return text

    try:
        client = _client()
        # Sarvam caps how much text one call can take, so long
        # explanations are translated paragraph by paragraph and
        # stitched back together. These are independent network calls,
        # so they run in parallel rather than one at a time - waiting
        # for each paragraph sequentially was the main reason
        # translation felt slow.
        paragraphs = [p for p in text.split("\n\n") if p.strip()]

        def _translate_one(p: str) -> str:
            return client.text.translate(
                input=p,
                source_language_code=source_language_code,
                target_language_code=target_language_code,
                model="sarvam-translate:v1",
            ).translated_text

        with ThreadPoolExecutor(max_workers=min(8, len(paragraphs) or 1)) as pool:
            translated = list(pool.map(_translate_one, paragraphs))
        return "\n\n".join(translated)
    except Exception as e:
        print(f"[error] Sarvam translation failed: {type(e).__name__}: {e}")  # was silently swallowed before - now visible in the server log
        return f"{text}\n\n[Translation unavailable ({e}); showing English instead.]"


# Sarvam's transliteration endpoint doesn't support every language this
# app offers translation for (notably Urdu isn't in its target list as
# of when this was written) - fall back to the original English text
# for anything unsupported rather than erroring the whole request.
_TRANSLITERATION_SUPPORTED = {
    "bn-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN",
    "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN",
}


def transliterate(text: str, target_language_code: str, source_language_code: str = "en-IN") -> str:
    """Converts the SOUND of text into the target script - "Nilhist-M"
    becomes "निलहिस्ट-एम", not an actual translation of meaning (which
    doesn't make sense for a brand name that isn't a real word). Used
    for medicine names specifically, so a low-literacy patient can read/
    sound them out, while the original English is still shown alongside
    for matching against the physical pill box."""
    if target_language_code == source_language_code:
        return text
    if target_language_code not in _TRANSLITERATION_SUPPORTED:
        return text  # unsupported language - show the English name as-is rather than fail

    try:
        client = _client()
        return client.text.transliterate(
            input=text,
            source_language_code=source_language_code,
            target_language_code=target_language_code,
        ).transliterated_text
    except Exception as e:
        print(f"[error] Sarvam transliteration failed: {type(e).__name__}: {e}")
        return text  # fall back to the English name rather than break the page
