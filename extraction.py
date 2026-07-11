"""
Reads a prescription photo with a vision model and pulls out the
medicines as structured JSON. Two backends, picked by config.OCR_PROVIDER:

  "claude" (default) - Claude's vision model. Costs money per call, but
                        this is the one whose handwriting-reading quality
                        got actually tested earlier in this project.
  "gemini"            - Google Gemini's free tier. Has native image
                        understanding at no cost, but read the privacy
                        note in the README before pointing it at real
                        prescriptions - free-tier traffic can be
                        reviewed/used by Google to improve their products.

Both return the exact same JSON shape, so the rest of the app doesn't
care which one ran.
"""
import base64
import json
import re

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

import config

PROMPT = """Look at this prescription image (it may be handwritten, and
may use Indian brand names). Read every medicine on it and return ONLY
valid JSON, no markdown fences, no extra text, in this shape:

{
  "patient_name": string or null,
  "medicines": [
    {
      "name": string,
      "dosage": string or null,
      "frequency": string or null,
      "duration": string or null,
      "instructions": string or null
    }
  ],
  "notes": string or null,
  "low_confidence": true or false
}

Set low_confidence to true if the handwriting was hard to read. Don't
invent medicines that aren't actually on the image."""


def _media_type(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        ext, "image/jpeg"
    )


def _as_text(content) -> str:
    """response.content from LangChain chat models isn't always a plain
    string - it can come back as a list of content parts (each either a
    string or a dict with a "text" key), especially from Gemini. This
    normalizes either shape into one string before parsing."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
        return "".join(parts)
    return str(content)


def _parse_response(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(f"Couldn't read the prescription clearly. Model said:\n{text}")

    data.setdefault("medicines", [])
    data.setdefault("low_confidence", False)
    return data


def _extract_with_claude(image_bytes: bytes, filename: str) -> dict:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set - check your .env file.")

    llm = ChatAnthropic(model=config.OCR_MODEL, max_tokens=1500, api_key=config.ANTHROPIC_API_KEY)
    b64_image = base64.standard_b64encode(image_bytes).decode()

    message = HumanMessage(content=[
        {"type": "image", "source": {"type": "base64", "media_type": _media_type(filename), "data": b64_image}},
        {"type": "text", "text": PROMPT},
    ])
    response = llm.invoke([message])
    return _parse_response(_as_text(response.content))


def _extract_with_gemini(image_bytes: bytes, filename: str) -> dict:
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set - check your .env file.")

    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL, google_api_key=config.GEMINI_API_KEY, max_output_tokens=1500
    )
    b64_image = base64.standard_b64encode(image_bytes).decode()
    data_uri = f"data:{_media_type(filename)};base64,{b64_image}"

    message = HumanMessage(content=[
        {"type": "image_url", "image_url": data_uri},
        {"type": "text", "text": PROMPT},
    ])
    response = llm.invoke([message])
    return _parse_response(_as_text(response.content))


def extract_prescription(image_bytes: bytes, filename: str = "prescription.jpg") -> dict:
    if config.OCR_PROVIDER == "gemini":
        return _extract_with_gemini(image_bytes, filename)
    return _extract_with_claude(image_bytes, filename)
