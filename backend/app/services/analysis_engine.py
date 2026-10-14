"""Multimodal analysis pipeline.

Inputs (symptoms, lab reports, medical images, profile, history) are processed
by independent, explainable modules and fused:

    symptoms ─┐
    reports ──┼─> rule-based scoring ─> red flags / urgency ─> care plan
    images ───┘          │                                        │
                         └──> WHO/CDC retrieval ──> AI explanation (LLM or mock)

The AI provider only *explains* the structured results; it does not produce
the condition ranking (except optional, clearly-labelled image observations).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import registry
from app.ai.base import ImageInput, LLMRequest
from app.core.config import get_settings
from app.models import MedicalHistoryEntry, MedicalReport, User
from app.services import retrieval
from app.services.care_plan import build_care_plan
from app.services.lab_parser import abnormal, parse_lab_values
from app.services.safety import DISCLAIMER, URGENCY_GUIDANCE, detect_red_flags, sanitize_payload, urgency_from
from app.services.scoring import ENGINE_VERSION, condition_by_key, score_conditions
from app.services.symptoms import LABELS, normalise

log = logging.getLogger(__name__)


class AnalysisInputError(ValueError):
    pass


def compute_age(dob: date | None, today: date | None = None) -> int | None:
    if not dob:
        return None
    today = today or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def compute_bmi(height_cm: float | None, weight_kg: float | None) -> float | None:
    if not height_cm or not weight_kg:
        return None
    return round(weight_kg / (height_cm / 100) ** 2, 1)


def profile_context(user: User, db: Session) -> dict:
    p = user.profile
    history = db.scalars(select(MedicalHistoryEntry).where(MedicalHistoryEntry.user_id == user.id)).all()
    chronic = list(p.chronic_conditions or []) if p else []
    chronic += [h.title for h in history if h.category == "condition" and h.is_ongoing and "family" not in (h.title + (h.details or "")).lower()]
    family = [f"{h.title} {h.details or ''}" for h in history if "family" in (h.title + " " + (h.details or "")).lower()]
    allergies = list(p.allergies or []) if p else []
    allergies += [h.title for h in history if h.category == "allergy"]
    meds = list(p.current_medications or []) if p else []
    meds += [h.title for h in history if h.category == "medication" and h.is_ongoing]
    return {
        "age": compute_age(p.date_of_birth) if p else None,
        "sex": p.sex if p else None,
        "bmi": compute_bmi(p.height_cm, p.weight_kg) if p else None,
        "is_pregnant": bool(p and p.is_pregnant),
        "smoker": bool(p and p.smoker),
        "alcohol_use": p.alcohol_use if p else None,
        "activity_level": p.activity_level if p else None,
        "chronic_conditions": list(dict.fromkeys(chronic)),
        "allergies": list(dict.fromkeys(allergies)),
        "current_medications": list(dict.fromkeys(meds)),
        "family_history": family,
    }


SYSTEM_PROMPT = """You are the explanation module of BookMyCare, a patient-education tool.
You receive structured, rule-based screening results. Explain them in clear, kind, plain language
(reading level ~ age 14) for the patient.
Strict rules:
- Never state or imply a diagnosis. Use phrases like "may be consistent with" and "a doctor can confirm".
- Do not add conditions that are not in the provided list.
- Never recommend specific medicines, doses, or changing prescribed treatment.
- If urgency is "emergency" or "urgent", the first sentence must tell the patient to seek care accordingly.
- Base report interpretation only on the provided lab values and reference ranges.
- Use the provided WHO/CDC excerpts where relevant; do not invent sources.
Respond with a JSON object with keys: "summary" (string, <= 120 words), "report_interpretation" (string, <= 100 words),
"questions_for_doctor" (array of 3-5 short strings)."""

IMAGE_SYSTEM_PROMPT = """You describe medical images for a patient-education prototype. You are not a radiologist and
must not diagnose. Describe only clearly visible, general observations (e.g. image type, body region, visible
abnormal-looking areas) and image quality. Respond with JSON: {"image_type": str, "observations": [str],
"possible_findings": [short neutral terms such as "consolidation", "rash", "pallor"], "quality": str,
"limitations": str}. If unsure, return empty lists."""


def _load_reports(db: Session, user: User, ids: list[int], kind: str) -> list[MedicalReport]:
    if not ids:
        return []
    rows = db.scalars(select(MedicalReport).where(MedicalReport.user_id == user.id, MedicalReport.id.in_(ids))).all()
    found = {r.id for r in rows}
    missing = [i for i in ids if i not in found]
    if missing:
        raise AnalysisInputError(f"Unknown file id(s): {missing}")
    wrong = [r.id for r in rows if r.kind != kind]
    if wrong:
        raise AnalysisInputError(f"File id(s) {wrong} are not of type '{kind}'")
    return list(rows)


def _image_observations(images: list[MedicalReport]) -> tuple[list[dict], list[str], dict | None]:
    """Run optional AI image observation. Returns (per-image results, finding terms, provider info)."""
    s = get_settings()
    results, findings = [], []
    provider_info = None
    for img in images:
        entry = {
            "report_id": img.id,
            "title": img.title,
            "report_type": img.report_type,
            "quality": img.image_features or {},
            "ai_observation": None,
        }
        path = s.upload_dir / img.stored_filename
        try:
            data = path.read_bytes()
        except OSError:
            entry["error"] = "Stored image file is missing."
            results.append(entry)
            continue
        req = LLMRequest(
            task="image_observation", system=IMAGE_SYSTEM_PROMPT,
            prompt=f"Image labelled by the patient as: {img.report_type or 'unspecified'} - {img.title}.",
            images=[ImageInput(img.content_type, data)], max_tokens=600,
        )
        outcome = registry.generate(req)
        resp = outcome.response
        provider_info = {"provider": resp.provider, "model": resp.model, "is_mock": resp.is_mock, "attempts": outcome.attempts}
        obs = resp.data or {}
        obs, removed = sanitize_payload(obs)
        entry["ai_observation"] = {
            "provider": resp.provider,
            "is_mock": resp.is_mock,
            "observations": [str(o) for o in obs.get("observations", [])][:8],
            "possible_findings": [str(o) for o in obs.get("possible_findings", [])][:8],
            "note": obs.get("note") or obs.get("limitations"),
            "quality": obs.get("quality"),
            "unverified": True,
        }
        if not resp.is_mock:
            findings.extend(entry["ai_observation"]["possible_findings"])
        results.append(entry)
    return results, findings, provider_info


def run_analysis(db: Session, user: User, payload) -> dict:
    t0 = time.perf_counter()
    reports = _load_reports(db, user, payload.report_ids, "report")
    images = _load_reports(db, user, payload.image_ids, "image")
    symptoms = normalise(payload.symptoms, payload.symptom_text)
    if not symptoms and not reports and not images:
        raise AnalysisInputError("Provide at least one symptom, a medical report or a medical image.")

    pctx = profile_context(user, db)

    # Labs: re-parse with the patient's sex so sex-specific ranges apply.
    labs: list[dict] = []
    report_summaries = []
    seen_keys: set[str] = set()
    for r in sorted(reports, key=lambda r: (r.report_date or date.min, r.id), reverse=True):
        vals = parse_lab_values(r.extracted_text, pctx["sex"]) if r.extracted_text else []
        for v in vals:
            if v["key"] not in seen_keys:  # most recent report wins
                v["report_id"] = r.id
                labs.append(v)
                seen_keys.add(v["key"])
        report_summaries.append({"report_id": r.id, "title": r.title, "extraction_status": r.extraction_status, "lab_count": len(vals)})
    abnormal_labs = abnormal(labs)

    image_results, image_findings, image_provider = _image_observations(images)

    conditions = score_conditions(symptoms, labs, pctx, payload.duration_days, image_findings)
    red_flags = detect_red_flags(symptoms, labs, pctx, payload.severity, payload.duration_days)
    urgency = urgency_from(red_flags, conditions, abnormal_labs)
    care_plan = build_care_plan(urgency, red_flags, conditions, abnormal_labs, pctx)

    # Retrieval
    topics: list[str] = []
    for c in conditions[:3]:
        topics += (condition_by_key(c["key"]) or {}).get("topics", [])
    if any(f["code"] in ("cardiac", "stroke") for f in red_flags):
        topics.append("emergency")
    if any(f["code"] == "self_harm" for f in red_flags):
        topics.append("mental_health")
    query = " ".join([c["name"] for c in conditions[:3]] + [LABELS.get(s, s) for s in symptoms[:6]] + [l["test"] for l in abnormal_labs[:4]])
    sources = retrieval.search(db, query, k=4, topics=topics) if query.strip() else []

    # AI explanation
    context = {
        "urgency": urgency,
        "symptom_labels": [LABELS.get(s, s) for s in symptoms],
        "conditions": [{k: c[k] for k in ("name", "match_score", "confidence")} | {"top_factors": [f["label"] for f in c["factors"][:4]]} for c in conditions],
        "abnormal_labs": [{k: l.get(k) for k in ("test", "value", "unit", "ref_low", "ref_high", "status")} for l in abnormal_labs],
        "lab_count": len(labs),
        "patient": {k: pctx[k] for k in ("age", "sex", "is_pregnant")},
        "red_flags": [f["title"] for f in red_flags],
        "sources": [{"title": s["title"], "excerpt": s["snippet"]} for s in sources],
    }
    req = LLMRequest(task="analysis_explanation", system=SYSTEM_PROMPT,
                     prompt="Screening results (JSON):\n" + json.dumps(context, ensure_ascii=False), context=context)
    outcome = registry.generate(req)
    resp = outcome.response
    expl_raw = resp.data or {"summary": resp.text}
    expl, removed = sanitize_payload(expl_raw)
    explanation = {
        "summary": str(expl.get("summary") or "").strip(),
        "report_interpretation": str(expl.get("report_interpretation") or "").strip(),
        "questions_for_doctor": [str(q) for q in (expl.get("questions_for_doctor") or [])][:6],
        "notice": expl.get("notice"),
        "safety_filtered_sentences": len(removed),
    }
    if urgency in ("emergency", "urgent") and not explanation["summary"].lower().startswith(("seek", "call", "please", "see a doctor", "go")):
        explanation["summary"] = f"{URGENCY_GUIDANCE[urgency]} {explanation['summary']}".strip()

    data_completeness = {
        "symptoms": bool(symptoms),
        "lab_values": bool(labs),
        "images": bool(images),
        "profile": bool(pctx["age"] is not None and pctx["sex"]),
    }
    limitations = [
        "Condition matches come from a transparent rule-based knowledge base with hand-set weights; they are not clinically validated and are not probabilities.",
        "Only conditions in the BookMyCare knowledge base can be suggested; your actual condition may not be listed.",
    ]
    if images:
        limitations.append(
            "Medical images are checked for quality only." if all((ir.get("ai_observation") or {}).get("is_mock", True) for ir in image_results)
            else "AI image observations come from a general-purpose vision model, are unverified, and carry only small weight."
        )
    if not labs and reports:
        limitations.append("No lab values could be read from the selected reports.")
    if not data_completeness["profile"]:
        limitations.append("Adding your age and sex to your profile improves reference ranges and personalisation.")

    return {
        "disclaimer": DISCLAIMER,
        "is_mock": resp.is_mock,
        "urgency": urgency,
        "urgency_guidance": URGENCY_GUIDANCE[urgency],
        "red_flags": red_flags,
        "symptoms": [{"key": s, "label": LABELS.get(s, s)} for s in symptoms],
        "conditions": conditions,
        "lab_values": labs,
        "abnormal_lab_count": len(abnormal_labs),
        "reports": report_summaries,
        "images": image_results,
        "care_plan": care_plan,
        "sources": sources,
        "explanation": explanation,
        "data_completeness": data_completeness,
        "limitations": limitations,
        "provenance": {
            "engine_version": ENGINE_VERSION,
            "explanation_provider": resp.provider,
            "explanation_model": resp.model,
            "provider_attempts": outcome.attempts,
            "image_provider": image_provider,
            "duration_ms": round((time.perf_counter() - t0) * 1000),
        },
    }
