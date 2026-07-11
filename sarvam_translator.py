"""
Translates the English explanation into the patient's chosen Indian
language with Sarvam's translate API - it's trained specifically on
Indian languages, which tends to read more naturally than asking a
general-purpose model to write directly in a lower-resource language.
"""
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
        # stitched back together.
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        translated = [
            client.text.translate(
                input=p,
                source_language_code=source_language_code,
                target_language_code=target_language_code,
                model="sarvam-translate:v1",
            ).translated_text
            for p in paragraphs
        ]
        return "\n\n".join(translated)
    except Exception as e:
        return f"{text}\n\n[Translation unavailable ({e}); showing English instead.]"
