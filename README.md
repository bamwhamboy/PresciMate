# 💊 PresciMate

Upload a photo of a prescription, get it explained in plain language in
your own language, download it as a PDF, and see your own past
prescriptions (nobody else can see them).

**One backend, one frontend**: a FastAPI backend (`api.py`) does all the
actual work; a Next.js/TypeScript frontend (`frontend/`) is the only UI.
(An earlier Streamlit version existed during development but has been
removed - this is the current, single source of truth.)

## How it works

1. **extraction.py** - a vision model (Claude or Gemini) reads the photo
   and returns the medicines as structured JSON.
2. **knowledge_base.py** - looks up each medicine in the Qdrant drug
   knowledge base (built by `build_knowledge_base.ipynb`), and checks for
   interactions by walking a small graph of known drug pairs (GraphRAG -
   "does A affect B" is a connections question, not a text-similarity one).
3. **explain.py** - an LLM writes a plain-English explanation grounded in
   what was retrieved above.
4. **formatting.py** - translates the dosage/frequency/duration/
   instructions fields and guarantees medicine names are reliably bolded
   in the explanation, regardless of what the LLM/translator did with
   markdown formatting.
5. **sarvam_translator.py** - Sarvam translates the explanation and
   medicine details into the language you picked. The medicine's
   brand/generic name is deliberately never translated - it's what's
   printed on the actual pill box, and translating it would make it
   harder, not easier, to match.
6. **pdf_export.py** - turns everything into a downloadable, branded PDF
   with the right Indic font embedded so it actually renders.
7. **pii.py** - strips the patient's name and redacts phone/email/ID
   numbers before anything reaches an external LLM or gets stored.
8. **hallucination_guard.py** - flags any dosage/frequency numbers in the
   explanation that don't appear anywhere in the actual prescription or
   retrieved reference material.
9. **api.py** + **jwt_auth.py** - the FastAPI backend and its
   token-based auth, tying all of the above together as HTTP endpoints
   for the Next.js frontend.

## Choosing providers (`.env`)

Both the OCR step and the explanation-writing step can run on Claude or
on Google Gemini's free tier, picked independently:

```
OCR_PROVIDER=claude    # or gemini
CHAT_PROVIDER=claude   # or gemini
```

**Before using Gemini with real prescriptions**: Google's free tier
terms state that unpaid traffic can be reviewed by humans and used to
improve their products - a real privacy tradeoff for actual medical
information. Their paid tier doesn't have this clause.

## Setup

1. **Build the knowledge base** (one-time) using `build_knowledge_base.ipynb`.
   Creates `qdrant_data/` and `prescribot.db`.

2. **Install backend dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **API keys** - copy `.env.example` to `.env` and fill in:
   - `ANTHROPIC_API_KEY` (console.anthropic.com / platform.claude.com)
   - `SARVAM_API_KEY` (dashboard.sarvam.ai)
   - `GEMINI_API_KEY` (aistudio.google.com) - only if using `gemini` for
     `OCR_PROVIDER` or `CHAT_PROVIDER`
   - `JWT_SECRET` - generate with:
     ```bash
     python3 -c "import secrets; print(secrets.token_hex(32))"
     ```

4. **Add a login** - copy `users.example.yaml` to `users.yaml`, or just
   use the Sign Up form in the app itself once it's running (it creates
   `users.yaml` automatically).

5. **Run the backend** (Terminal 1):
   ```bash
   uvicorn api:app --reload --port 8000
   ```

6. **Run the frontend** (Terminal 2):
   ```bash
   cd frontend
   cp .env.local.example .env.local
   npm install
   npm run dev
   ```

7. Open **http://localhost:3000**.

## Files

| File | Purpose |
|---|---|
| `api.py` | FastAPI backend - all HTTP endpoints |
| `jwt_auth.py` | Login/signup, JWT tokens |
| `config.py` | Settings, language codes, font paths |
| `extraction.py` | Vision OCR (Claude or Gemini) |
| `knowledge_base.py` | Vector search + GraphRAG + per-user history in Qdrant |
| `explain.py` | Writes the explanation (English) |
| `formatting.py` | Medicine field translation + reliable bolding |
| `sarvam_translator.py` | Translates into the chosen Indian language |
| `pdf_export.py` | Builds the downloadable PDF |
| `pii.py` | Strips identifying details before external calls/storage |
| `hallucination_guard.py` | Flags ungrounded numeric claims |
| `frontend/` | The Next.js/TypeScript UI - the only frontend |

## A couple of honest limitations

- Login is a YAML file + bcrypt - fine for a handful of real users, not
  built for scale.
- The hallucination guardrail is a heuristic on numbers specifically,
  not full semantic fact-checking.
- No eval suite yet measuring OCR/translation accuracy - would need a
  labeled test set of real prescriptions first.
