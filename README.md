# 💊 PresciMate

Upload a photo of a prescription, get it explained in plain language in
your own language, download it as a PDF, and see your own past
prescriptions (nobody else can see them).

## How it works

1. **extraction.py** - a vision model reads the photo and returns
   the medicines as structured JSON.
2. **knowledge_base.py** - looks up each medicine in the Qdrant drug
   knowledge base (built by `build_knowledge_base.ipynb`), and checks for
   interactions by walking a small graph of known drug pairs (GraphRAG -
   "does A affect B" is a connections question, not a text-similarity one).
3. **explain.py** - an LLM writes a plain-English explanation grounded in
   what was retrieved above.
4. **sarvam_translator.py** - Sarvam translates that explanation into the
   language you picked.
5. **pdf_export.py** - turns the translated explanation into a downloadable
   PDF, with the right Indic font embedded so it actually renders.
6. Everything is stored per-user in Qdrant (`knowledge_base.save_prescription`),
   tagged with your username, so your history tab only ever shows your
   own prescriptions.

## Choosing providers (`.env`)

Both the OCR step (`extraction.py`) and the explanation-writing step
(`explain.py`) can run on Claude or on Google Gemini's free tier, picked
independently:

```
OCR_PROVIDER=claude    # or gemini
CHAT_PROVIDER=claude   # or gemini
```

| Provider | Cost | Privacy | Quality |
|---|---|---|---|
| `claude` (default, both steps) | Pay-per-use | Standard API terms - not used to train models | OCR handwriting quality tested directly in this project |
| `gemini` (both steps) | Free tier available | ⚠️ Free-tier traffic may be reviewed by Google to improve their products | Untested on real handwritten Indian prescriptions - try it and judge for yourself |

**Set both to `gemini` and the only paid key left is Sarvam** (for
translation) - everything else runs free. **Before you do that with real
prescriptions**, think about the privacy tradeoff: Google's free-tier
terms say unpaid traffic can be reviewed by humans and used to improve
their products. That's a different privacy bar than most people would
want for someone's actual health information. Gemini's *paid* tier
doesn't have this clause, but then it isn't free anymore either.

To use Gemini for either step, add to `.env`:
```
GEMINI_API_KEY=your-key-here
```
Get a key at **aistudio.google.com** - keep billing disabled on that
Google Cloud project to stay on the free tier (enabling billing removes
free-tier access for that project entirely). The same key works for
both `OCR_PROVIDER=gemini` and `CHAT_PROVIDER=gemini`.

No semantic routing, no separate structuring model, no guardrails module -
kept deliberately simple. A short safety net (the disclaimer, and the
LLM being told never to suggest changing a dose) is baked into the
prompts in `explain.py` instead of a separate layer.

## Setup

1. **Build the knowledge base** (one-time) using `build_knowledge_base.ipynb`.
   This creates `qdrant_data/` and `prescribot.db`.

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **API keys:**
   ```bash
   cp .env.example .env
   # add ANTHROPIC_API_KEY (console.anthropic.com) - required unless
   #   both OCR_PROVIDER and CHAT_PROVIDER are set to gemini
   # add SARVAM_API_KEY   (dashboard.sarvam.ai) - always required
   # add GEMINI_API_KEY   (aistudio.google.com) - only if using gemini
   #   for either OCR_PROVIDER or CHAT_PROVIDER
   ```

4. **Add a user:**
   ```bash
   cp users.example.yaml users.yaml
   python3 -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
   # paste that hash into users.yaml under your username
   ```

5. **Run it:**
   ```bash
   streamlit run app.py
   ```

## Files

| File | What it does |
|---|---|
| `config.py` | Settings, language codes, font paths, disclaimer |
| `auth.py` | Login form + bcrypt password check |
| `extraction.py` | Vision model reads the prescription (Claude or Gemini, see below) |
| `knowledge_base.py` | Vector search, interaction graph, per-user history in Qdrant |
| `explain.py` | Writes the explanation (English), Claude or Gemini |
| `sarvam_translator.py` | Translates into the chosen Indian language |
| `pdf_export.py` | Builds the downloadable PDF with embedded Indic fonts |
| `app.py` | The Streamlit app itself |
| `fonts/` | Noto Sans fonts for each script (bundled so it works offline) |

## A couple of honest limitations

- Login is a simple YAML file + bcrypt - fine for a handful of real
  users, not built for self-serve signup at scale.
- Follow-up questions get a simple keyword check (`config.EMERGENCY_KEYWORDS`)
  before anything goes to the LLM - if it matches, the question never
  reaches Claude and a fixed safety message is shown instead. It's a
  plain substring check, not a smart classifier, so it'll miss anything
  phrased in a way the keyword list doesn't cover. Good enough as a
  basic safety net, not a substitute for real triage.
