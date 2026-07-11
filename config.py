"""
Settings for PresciMate. Locally, everything reads from a .env file (copy
.env.example to .env and fill it in). If this is deployed on Streamlit
Community Cloud, .env files don't exist there - Streamlit uses its own
Secrets manager instead - so _get_secret() checks st.secrets first and
falls back to the local .env value.
"""
import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str, default: str = "") -> str:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass  # no secrets.toml / not running on Streamlit Cloud - that's fine locally
    return os.getenv(key, default)


ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY")
SARVAM_API_KEY = _get_secret("SARVAM_API_KEY")
GEMINI_API_KEY = _get_secret("GEMINI_API_KEY")

# Which vision model reads the prescription photo: "claude" or "gemini".
# Gemini has a genuinely free tier with built-in image understanding, but
# read the README's privacy note before using it for real prescriptions -
# free-tier Gemini traffic can be reviewed/used by Google to improve their
# products, which matters when the image is someone's actual medical info.
OCR_PROVIDER = _get_secret("OCR_PROVIDER", "claude")

# Which model writes the plain-English explanation: "claude" or "gemini".
# Text-only step, no vision needed, so Gemini's free tier is a
# straightforward fit here (the same privacy note from OCR_PROVIDER
# applies - see README).
CHAT_PROVIDER = _get_secret("CHAT_PROVIDER", "claude")

OCR_MODEL = _get_secret("OCR_MODEL", "claude-sonnet-5")      # used when OCR_PROVIDER=claude
GEMINI_MODEL = _get_secret("GEMINI_MODEL", "gemini-3.1-flash-lite")  # used when OCR_PROVIDER or CHAT_PROVIDER=gemini
# Google's Gemini model names churn frequently - gemini-2.5-flash, the
# original default here, was deprecated for new users within weeks of
# being set. If this stops working, check the current list at
# ai.google.dev/gemini-api/docs/models and set GEMINI_MODEL in your
# .env/secrets.toml, no code change needed.
CHAT_MODEL = _get_secret("CHAT_MODEL", "claude-sonnet-5")  # used when CHAT_PROVIDER=claude

# Knowledge base paths - must match what build_knowledge_base.ipynb created
QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_data")
DRUG_COLLECTION = os.getenv("DRUG_COLLECTION", "drug_knowledge")   # built by the notebook
USER_COLLECTION = os.getenv("USER_COLLECTION", "user_prescriptions")  # created by this app
DB_PATH = os.getenv("DB_PATH", "prescribot.db")  # matches build_knowledge_base.ipynb's DB_PATH
DENSE_MODEL = os.getenv("DENSE_MODEL", "BAAI/bge-small-en-v1.5")

USERS_FILE = os.getenv("USERS_FILE", "users.yaml")

# Language name -> Sarvam's language code, and the local font file used to
# render that language in the PDF (reportlab's built-in fonts don't have
# Indic glyphs, so each script needs its own Noto font registered).
LANGUAGES = {
    "English":   {"code": "en-IN", "font": None},  # built-in Helvetica is fine for English
    "Hindi":     {"code": "hi-IN", "font": "fonts/NotoSansDevanagari-Regular.ttf"},
    "Marathi":   {"code": "mr-IN", "font": "fonts/NotoSansDevanagari-Regular.ttf"},
    "Bengali":   {"code": "bn-IN", "font": "fonts/NotoSansBengali-Regular.ttf"},
    "Tamil":     {"code": "ta-IN", "font": "fonts/NotoSansTamil-Regular.ttf"},
    "Telugu":    {"code": "te-IN", "font": "fonts/NotoSansTelugu-Regular.ttf"},
    "Gujarati":  {"code": "gu-IN", "font": "fonts/NotoSansGujarati-Regular.ttf"},
    "Kannada":   {"code": "kn-IN", "font": "fonts/NotoSansKannada-Regular.ttf"},
    "Malayalam": {"code": "ml-IN", "font": "fonts/NotoSansMalayalam-Regular.ttf"},
    "Punjabi":   {"code": "pa-IN", "font": "fonts/NotoSansGurmukhi-Regular.ttf"},
    "Odia":      {"code": "od-IN", "font": "fonts/NotoSansOriya-Regular.ttf"},
    "Urdu":      {"code": "ur-IN", "font": "fonts/NotoNaskhArabic-Regular.ttf"},
}

DISCLAIMER = (
    "PresciMate explains what your doctor already prescribed. It does not "
    "diagnose or replace medical advice - always follow your doctor's or "
    "pharmacist's instructions. In an emergency, contact a doctor or local "
    "emergency services right away."
)

# Simple keyword check - if a follow-up question mentions something that
# sounds urgent, skip the LLM entirely and show a fixed safety message
# instead of letting a model improvise mid-emergency.
EMERGENCY_KEYWORDS = [
    "can't breathe", "cannot breathe", "difficulty breathing",
    "chest pain", "throat is swelling", "throat swelling",
    "anaphylaxis", "allergic reaction", "unconscious", "unresponsive",
    "overdose", "took too many", "seizure", "severe bleeding",
    "want to end my life", "kill myself", "hurt myself", "suicide",
]

EMERGENCY_MESSAGE = (
    "This sounds like it could be a medical emergency. PresciMate can't "
    "help with urgent symptoms - please contact your local emergency "
    "number or go to the nearest emergency room right away. If you're "
    "having thoughts of harming yourself, please reach out to a crisis "
    "helpline or emergency services immediately."
)
