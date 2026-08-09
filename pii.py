"""
PII protection for PresciMate.

The core idea: the patient's name and any other identifying details
(phone numbers, emails, ID numbers) never need to leave the user's own
browser session to explain what a medicine does. So before anything gets
sent to an external LLM provider (Claude/Gemini/Sarvam) or stored in
Qdrant, this strips that out. The name still displays fine in the app's
own UI and in the downloaded PDF - those stay local to the user - this
only guards what crosses a network boundary or gets persisted.

This is regex/pattern-based, not a full NER model - it catches the
common, high-confidence cases (phone numbers, emails, Aadhaar/PAN-style
ID patterns, the extracted patient_name field itself) rather than trying
to catch every possible way a name could appear in free text. Worth
knowing that limit rather than assuming it's airtight.
"""
import re

# Indian phone numbers (10 digits, optionally with +91/0 prefix),
# email addresses, Aadhaar (12 digits, often spaced in groups of 4),
# and PAN (5 letters + 4 digits + 1 letter) patterns.
_PHONE_RE = re.compile(r"(?:\+91[\-\s]?|0)?[6-9]\d{9}\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")

_PATTERNS = {
    "phone number": _PHONE_RE,
    "email address": _EMAIL_RE,
    "Aadhaar-like number": _AADHAAR_RE,
    "PAN-like number": _PAN_RE,
}


def scan_for_pii(text: str) -> list[str]:
    """Returns a list of PII categories found in the text, e.g.
    ["phone number", "email address"]. Empty list if none found."""
    if not text:
        return []
    found = []
    for label, pattern in _PATTERNS.items():
        if pattern.search(text):
            found.append(label)
    return found


def redact_pii_text(text: str) -> str:
    """Replaces any matched PII patterns with a [REDACTED] marker."""
    if not text:
        return text
    for pattern in _PATTERNS.values():
        text = pattern.sub("[REDACTED]", text)
    return text


def sanitize_for_external(extracted: dict) -> dict:
    """Returns a copy of the extracted prescription data with the
    patient's name removed and any PII patterns scrubbed from free-text
    fields (notes, instructions). Use this for anything that goes to an
    LLM API or into Qdrant storage - never the raw extracted dict."""
    safe = dict(extracted)
    safe.pop("patient_name", None)

    if safe.get("notes"):
        safe["notes"] = redact_pii_text(safe["notes"])

    safe["medicines"] = [
        {
            **m,
            "instructions": redact_pii_text(m.get("instructions") or "") or None,
        }
        for m in safe.get("medicines", [])
    ]
    return safe
