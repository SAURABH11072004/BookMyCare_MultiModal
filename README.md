# BookMyCare

**An explainable, multimodal, patient-centred health screening assistant** — final-year B.Tech Computer Engineering project
based on the concept *"An Explainable Multimodal AI Framework for Disease Detection, Medical Report Interpretation, and Personalized Care Pathway Recommendation"*.

> ⚠️ **Educational prototype.** BookMyCare does not diagnose disease and is not a medical device. All outputs are screening
> suggestions to discuss with a qualified clinician. Sample data in this repository is synthetic.

## What works today

| Area | Status |
|---|---|
| Accounts | Register / login (bcrypt + JWT), per-user data isolation |
| Patient profile | Age, sex, BMI, pregnancy, lifestyle, allergies, conditions, medicines |
| Medical history | Timeline CRUD (conditions, surgeries, medicines, allergies, vaccinations, visits) |
| Report upload | PDF (text layer), scanned PDF / photo (Tesseract OCR, optional), TXT/CSV; magic-byte type check, 15 MB limit |
| Report interpretation | Recognises ~27 common lab tests + blood pressure, unit conversion (mmol/L, g/L, /µL), sex-specific ranges, critical values |
| Medical images | Upload + explainable quality checks (resolution, brightness, contrast, blur). Optional *unverified* observations from a vision LLM (Gemini). **No trained diagnostic imaging model is included.** |
| Multimodal screening | Transparent rule-based engine fusing symptoms, lab values, profile risk factors, duration and (optional) image observations across 22 conditions |
| Explainability | Every match shows contributing factors with points and share, evidence *against*, missing typical features, score decomposition |
| Confidence | Heuristic evidence-match score (not a probability) + low / moderate / high confidence label |
| Safety | Red-flag triage (cardiac, stroke, breathing, meningitis, self-harm, dengue warning signs, critical labs, BP crisis, pregnancy…), urgency levels, AI output sanitiser (removes dosing / diagnostic claims / "stop your medicine"), disclaimers |
| Care pathway | Personalised plan: immediate actions, self-care, when to see a doctor, tests, specialists, profile-specific advice |
| WHO / CDC retrieval | BM25 search over 37 curated summaries (with source links) + an ingestion script that indexes live who.int / cdc.gov pages |
| AI providers | Common interface for Gemini, Groq, OpenRouter with automatic fallback; **mock mode** (clearly labelled) when no keys are set |
| UI | Responsive React app: dashboard, profile, history, reports, analysis wizard, explainable results (printable), health library |
| Tests | 50 backend tests (pytest), 10 frontend tests (Vitest), end-to-end browser smoke test performed during development |

## Tech stack

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, React Router, lucide-react, Vitest + Testing Library
- **Backend:** FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, PyJWT, bcrypt, pypdf, pypdfium2, Pillow, pytesseract, httpx
- **Database:** SQLite by default (`backend/bookmycare.db`); any SQLAlchemy URL via `DATABASE_URL`
- **AI:** Gemini / Groq / OpenRouter via REST, mock fallback

## Run locally (Windows)

Prerequisites: **Python 3.10+** (3.12 recommended), **Node.js 20+**, Git (optional).
Optional: [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) for scanned reports.

```powershell
cd D:\BTECH-BookMyCare
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1     # one-time: venv, deps, .env, DB, demo user, npm ci

# terminal 1
powershell -ExecutionPolicy Bypass -File scripts\run-backend.ps1    # http://127.0.0.1:8000  (API docs at /docs)
# terminal 2
powershell -ExecutionPolicy Bypass -File scripts\run-frontend.ps1   # http://localhost:5173
```

Sign in with the synthetic demo account **demo@bookmycare.dev / DemoPass123**, or register a new account.

<details><summary>Manual steps (any OS)</summary>

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env  — then set JWT_SECRET
alembic upgrade head              # also runs automatically on server start
python -m scripts.seed_demo       # optional synthetic demo user
uvicorn app.main:app --reload

cd ../frontend
npm ci
npm run dev
```
</details>

### Enabling real AI providers

Put one or more keys in `backend/.env` and restart the backend — no code changes needed:

```
GEMINI_API_KEY=...        # also enables optional image observations
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
AI_PROVIDER_ORDER=gemini,groq,openrouter
```

The first configured provider is used; if a call fails (network, quota, invalid JSON) the next one is tried, ending with the
mock provider. The result page always shows which provider produced the explanation. The LLM only *explains* the rule-based
results — it does not decide the condition ranking — and its output passes through the safety sanitiser.

### OCR for scanned reports

Install Tesseract and, if it is not on `PATH`, set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` in `backend/.env`.
Without it, text PDFs and TXT files still work; scanned files are stored and marked "Not extracted".

### Index live WHO / CDC pages (optional)

```powershell
cd backend
.\.venv\Scripts\python -m scripts.ingest_who_cdc                      # pages listed in app/data/health_corpus.json
.\.venv\Scripts\python -m scripts.ingest_who_cdc https://www.who.int/news-room/fact-sheets/detail/malaria
```

Only `https://www.who.int` and `https://www.cdc.gov` URLs are accepted. The app shows short excerpts with links to the source.

## Tests

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test-all.ps1
# or individually
cd backend;  .\.venv\Scripts\python -m pytest -q
cd frontend; npm test; npm run build
```

Backend tests use a temporary database and force mock AI mode; HTTP provider tests stub the network, so no keys are needed.

## Project layout

```
backend/
  app/
    ai/            provider interface, Gemini/Groq/OpenRouter adapters, mock provider, fallback registry
    api/routes/    auth, profile+history, reports, analyses, knowledge, system
    services/      extraction (PDF/OCR/image quality), lab_parser, symptoms, scoring, safety,
                   care_plan, retrieval (BM25), analysis_engine (pipeline)
    data/          conditions.json (screening knowledge base), health_corpus.json (WHO/CDC summaries)
    models/ schemas/ db/ core/
  alembic/         migrations
  scripts/         seed_demo, ingest_who_cdc, make_sample_data
  sample_data/     synthetic reports and image
  tests/
frontend/
  src/pages/       Auth, Dashboard, Profile, History, Reports, ReportDetail, NewAnalysis, AnalysisResult, Analyses, Library
  src/components/  layout, UI kit, lab table, badges
  src/lib/         API client, auth context, types, formatting
docs/ARCHITECTURE.md
scripts/           setup / run / test helpers (PowerShell + bash)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the pipeline, scoring method, safety design and roadmap.
