"""
FastAPI backend for PresciMate. Wraps the same modules the Streamlit app
uses (extraction, knowledge_base, explain, sarvam_translator, pdf_export,
pii, hallucination_guard) behind a REST API, so the Next.js frontend has
something to call. Nothing about the actual pipeline changes here - this
is purely a new way to reach it.

Run with: uvicorn api:app --reload --port 8000
"""
import io

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import explain
import extraction
import formatting
import hallucination_guard
import jwt_auth
import knowledge_base as kb
import pdf_export
import pii
import sarvam_translator

app = FastAPI(title="PresciMate API")


def _clean_error(e: Exception, fallback: str) -> str:
    """Upstream API failures (Anthropic, Gemini, Sarvam) can surface raw
    HTML error pages or long stack-trace-like strings in the exception
    message - never show that directly to a patient. Logs the real error
    server-side (visible in the uvicorn terminal) and returns a clean
    message for the client instead."""
    print(f"[error] {type(e).__name__}: {e}")  # full detail stays in the server log
    raw = str(e)
    if "<html" in raw.lower() or "<!doctype" in raw.lower() or len(raw) > 300:
        return fallback
    return raw

# Next.js dev server + whatever production origin you deploy the
# frontend to. Tighten this to your real domain before going live -
# "*" during local development only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
# Auth
# ------------------------------------------------------------------ #
class SignupRequest(BaseModel):
    name: str
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    name: str
    username: str


def get_current_user(authorization: str = Header(default="")) -> dict:
    """FastAPI dependency: every protected route takes this as a param
    and gets back {"username": ..., "name": ...}, or a 401 if the
    Authorization: Bearer <token> header is missing/invalid."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return jwt_auth.verify_token(token)
    except jwt_auth.AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest):
    try:
        token = jwt_auth.signup(req.name, req.username, req.password)
    except jwt_auth.AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_clean_error(e, "Something went wrong creating your account - please try again."),
        )
    return AuthResponse(token=token, name=req.name, username=req.username)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    try:
        token = jwt_auth.login(req.username, req.password)
    except jwt_auth.AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_clean_error(e, "Something went wrong logging in - please try again."),
        )
    identity = jwt_auth.verify_token(token)
    return AuthResponse(token=token, name=identity["name"], username=identity["username"])


# ------------------------------------------------------------------ #
# Prescriptions
# ------------------------------------------------------------------ #
@app.post("/api/prescriptions/extract")
async def extract_prescription(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    image_bytes = await file.read()
    try:
        extracted = extraction.extract_prescription(image_bytes, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=_clean_error(e, "Couldn't read the prescription right now - please try again."),
        )
    return extracted


class ExplainRequest(BaseModel):
    medicines: list[dict]
    language: str


@app.post("/api/prescriptions/explain")
def explain_prescription(req: ExplainRequest, user: dict = Depends(get_current_user)):
    if req.language not in config.LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unknown language: {req.language}")
    language_code = config.LANGUAGES[req.language]["code"]

    try:
        drug_names = [m["name"] for m in req.medicines]
        drug_context = "\n\n".join(kb.search_drug_knowledge(name) for name in drug_names)
        interactions = kb.check_interactions(drug_names)

        # PII guardrail - same as the Streamlit app: strip identifying
        # details before anything reaches an external LLM or storage.
        safe = pii.sanitize_for_external({"medicines": req.medicines})
        safe_medicines = safe["medicines"]

        english_explanation = explain.write_explanation(safe_medicines, drug_context, interactions)
        grounding = hallucination_guard.check_grounding(english_explanation, safe_medicines, drug_context)
        final_explanation = sarvam_translator.translate(english_explanation, language_code)

        # Translate dosage/frequency/duration/instructions and add the
        # transliterated name (name_local) for on-screen display - the
        # untranslated "name" field is kept too, for matching against
        # the physical pill box.
        translated_medicines = formatting.translate_medicine_fields(req.medicines, language_code)

        # Swap the medicine name for its transliterated + bolded form
        # inside the explanation text itself, so it reads naturally in
        # the target language rather than having an English name appear
        # mid-sentence.
        final_explanation = formatting.apply_transliterated_names(final_explanation, translated_medicines)

        kb.save_prescription(user["username"], safe_medicines, final_explanation, req.language)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=_clean_error(e, "Couldn't write the explanation right now - please try again."),
        )

    return {
        "explanation": final_explanation,
        "interactions": interactions,
        "grounding": grounding,
        "translated_medicines": translated_medicines,
    }


class AskRequest(BaseModel):
    question: str
    medicines: list[dict]
    language: str


@app.post("/api/prescriptions/ask")
def ask_question(req: AskRequest, user: dict = Depends(get_current_user)):
    if req.language not in config.LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unknown language: {req.language}")
    language_code = config.LANGUAGES[req.language]["code"]

    if any(kw in req.question.lower() for kw in config.EMERGENCY_KEYWORDS):
        return {
            "answer": sarvam_translator.translate(config.EMERGENCY_MESSAGE, language_code),
            "grounding": {"flagged": False, "ungrounded_claims": []},
            "emergency": True,
        }

    try:
        safe = pii.sanitize_for_external({"medicines": req.medicines})
        safe_medicines = safe["medicines"]

        prescription_details = "\n".join(
            f"{m['name']}: dosage={m.get('dosage') or 'not specified'}, "
            f"frequency={m.get('frequency') or 'not specified'}, "
            f"duration={m.get('duration') or 'not specified'}, "
            f"instructions={m.get('instructions') or 'not specified'}"
            for m in safe_medicines
        )
        general_context = "\n\n".join(kb.search_drug_knowledge(m["name"]) for m in req.medicines)
        drug_context = f"From this prescription:\n{prescription_details}\n\nGeneral drug info:\n{general_context}"

        answer_en = explain.answer_question(req.question, drug_context)
        grounding = hallucination_guard.check_grounding(answer_en, safe_medicines, drug_context)
        answer = sarvam_translator.translate(answer_en, language_code)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=_clean_error(e, "Couldn't answer that right now - please try again."),
        )

    return {"answer": answer, "grounding": grounding, "emergency": False}


@app.get("/api/prescriptions/history")
def get_history(user: dict = Depends(get_current_user)):
    return kb.get_user_history(user["username"])


class PdfRequest(BaseModel):
    medicines: list[dict]
    explanation: str
    language: str


@app.post("/api/prescriptions/pdf")
def generate_pdf(req: PdfRequest, user: dict = Depends(get_current_user)):
    from fastapi.responses import StreamingResponse

    path = f"/tmp/prescimate_{user['username']}.pdf"
    pdf_export.build_pdf(path, req.medicines, req.explanation, req.language)
    with open(path, "rb") as f:
        buffer = io.BytesIO(f.read())
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=prescription_explained.pdf"},
    )


@app.get("/api/languages")
def get_languages():
    return {"languages": list(config.LANGUAGES.keys())}


@app.get("/api/health")
def health():
    return {"status": "ok"}
