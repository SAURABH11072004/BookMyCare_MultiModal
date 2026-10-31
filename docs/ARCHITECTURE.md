# BookMyCare architecture

## Analysis pipeline

```
 Symptoms (chips + free text) ─► symptom normaliser (synonyms, negation) ─┐
 Lab reports ─► extraction (pdf text / OCR) ─► lab parser (ranges, units) ─┼─► rule-based scorer ─► ranked conditions + factors
 Medical images ─► quality features  [+ optional vision-LLM observations] ─┤                │
 Profile & history ─► risk-factor context (age, BMI, sex, pregnancy…) ─────┘                ▼
                                                             safety layer (red flags, urgency)
                                                                          ▼
                                       care-plan builder (personalised)   WHO/CDC BM25 retrieval
                                                                          ▼
                                     AI explanation (Gemini/Groq/OpenRouter or mock) ─► sanitiser
                                                                          ▼
                                       stored Analysis (inputs + full result JSON + provenance)
```

`app/services/analysis_engine.py` orchestrates the steps. Each step is deterministic except the AI explanation and the
optional image observation; those are clearly labelled with their provider.

## Grounded assessment (AI + retrieval)

`services/grounding.py` sits between the rule engine and the language model:

1. **Evidence** - `gather_evidence()` retrieves WHO/CDC passages (BM25, topic-matched) for each of the top three conditions, for red-flag topics (emergency, stroke, mental health) and for the patient's own history (e.g. diabetes, asthma, smoking). Passages are numbered `S1…S8`.
2. **Context** - `build_context()` gives the model the scored conditions (supporting / against / missing evidence), lab values, patient history, the fixed urgency and the numbered passages.
3. **Generation** - `registry.generate()` tries providers in order; `validate_ai_response()` rejects unusable replies so the next provider is tried. Failures keep their kind (`rate_limited`, `auth_error`, `model_not_found`, `timeout`, `invalid_response`, …).
4. **Cleaning** - `clean_ai_output()` drops citation ids that were not retrieved, notes about unknown conditions, diagnostic assertions, dosing, "stop your medicine" and "no need to see a doctor" sentences, and always puts the rule-based urgency guidance first for urgent results.
5. **Assessment** - `build_assessment()` returns one structured block: possible conditions (unconfirmed, with supporting / against evidence, history considered, citations, uncertainty), overall uncertainty, limitations, next steps, citations and an explicit `ai` status (`generated | mock | failed | skipped_emergency`).

Emergency urgency skips the model completely. `is_mock` is true only when template text is shown.

## Scoring (explainable)

For each condition in `app/data/conditions.json`:

* **Symptoms** add their weight when reported.
* **Lab rules** add weight when a value deviates in the expected direction (×0.7 mild, ×1.0 marked, ×1.25 critical).
  Strongly weighted labs that are *normal* subtract points (evidence against).
* **Risk factors** (age, BMI, smoking, alcohol, activity, sex, pregnancy, chronic and family history) add small weights,
  but cannot create a match on their own.
* **Duration** adds weight for chronic patterns (e.g. TB, typhoid) and penalises conditions whose usual course is exceeded.
* **Image observations** (only from a real vision provider, unverified) add small weights via a keyword map.

`match = 0.5 × saturation + 0.5 × coverage`, where saturation = `1 − exp(−1.6 · points / scale)` and coverage is the
share of the condition's observable characteristic features that are present. Lab-defined conditions (diabetes, anaemia,
thyroid, kidney, liver, lipids, vitamins) are capped at 45% without lab evidence. Confidence is *high* only with ≥ 70%
match and either two evidence modalities or a strong lab-defined match.

These weights are hand-set for an explainable prototype and **are not clinically validated**.

## Safety design

1. Red-flag rules run independently of scoring and always override urgency.
2. Crisis messaging for self-harm phrases, with configurable emergency number / helpline (`EMERGENCY_NUMBER`, `CRISIS_LINE`).
3. The LLM receives only structured results and is instructed not to diagnose or prescribe; its output is post-filtered to
   remove sentences with dosages, definitive diagnoses or instructions to change medicines.
4. Mock mode is visible in the UI banner, the result badge and the explanation text.
5. Every result includes the disclaimer, limitations and provenance (engine version, provider, fallbacks).

## Data model

`users` 1–1 `patient_profiles`; `users` 1–n `medical_history`, `medical_reports` (kind = report | image), `analyses`;
`health_documents` (curated or ingested WHO/CDC text). Migrations live in `backend/alembic/versions`.

## Roadmap / not yet implemented

* Trained, validated imaging models (e.g. chest X-ray classifier) behind the existing image interface.
* Vector embeddings for hybrid BM25 + dense retrieval, and a patient-facing question-answer chat built on the same evidence + citation layer.
* Evaluation framework with labelled synthetic vignettes (precision@k, red-flag recall).
* Clinician role, appointment booking, report sharing, audit log, rate limiting, refresh tokens.
* Multilingual explanations.
