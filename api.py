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
import hallucination_guard
import jwt_auth
import knowledge_base as kb
import pdf_export
import pii
import sarvam_translator

app = FastAPI(title="PresciMate API")

# Next.js dev server + whatever production origin you deploy the
# frontend to. Tighten this to your real domain before going live -
# "*" during local development only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
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
    return AuthResponse(token=token, name=req.name, username=req.username)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    try:
        token = jwt_auth.login(req.username, req.password)
    except jwt_auth.AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
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
        raise HTTPException(status_code=422, detail=str(e))
    return extracted


class ExplainRequest(BaseModel):
    medicines: list[dict]
    language: str


@app.post("/api/prescriptions/explain")
def explain_prescription(req: ExplainRequest, user: dict = Depends(get_current_user)):
    if req.language not in config.LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unknown language: {req.language}")
    language_code = config.LANGUAGES[req.language]["code"]

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

    kb.save_prescription(user["username"], safe_medicines, final_explanation, req.language)

    return {
        "explanation": final_explanation,
        "interactions": interactions,
        "grounding": grounding,
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
