"""Safety layer: red-flag detection, urgency triage and output sanitisation."""
from __future__ import annotations

import re

from app.core.config import get_settings

URGENCY_ORDER = ["routine", "soon", "urgent", "emergency"]

DISCLAIMER = (
    "BookMyCare provides educational screening information only. It is not a medical diagnosis and "
    "does not replace a qualified healthcare professional. Always consult a doctor about your health, "
    "and seek emergency care if you feel your condition is serious."
)


def max_urgency(*levels: str) -> str:
    return max(levels, key=URGENCY_ORDER.index) if levels else "routine"


def _flag(code: str, level: str, title: str, message: str) -> dict:
    return {"code": code, "level": level, "title": title, "message": message}


def detect_red_flags(
    symptoms: list[str],
    labs: list[dict],
    profile_ctx: dict,
    severity: str | None = None,
    duration_days: int | None = None,
) -> list[dict]:
    s = set(symptoms)
    settings = get_settings()
    em = settings.emergency_number
    flags: list[dict] = []

    if "self_harm_thoughts" in s:
        flags.append(_flag(
            "self_harm", "emergency", "You mentioned thoughts of self-harm",
            f"You don't have to go through this alone. Please contact {settings.crisis_line} or emergency services ({em}) now, "
            "or reach out to someone you trust and stay with them.",
        ))
    if "chest_pain" in s and (s & {"shortness_of_breath", "sweating", "nausea", "dizziness", "fainting"} or severity == "severe"):
        flags.append(_flag("cardiac", "emergency", "Possible heart attack warning signs",
                           f"Chest pain with breathlessness, sweating, nausea or light-headedness can signal a heart attack. Call {em} immediately."))
    elif "chest_pain" in s:
        flags.append(_flag("chest_pain", "urgent", "Chest pain needs assessment",
                           f"Chest pain should be checked by a doctor promptly. If it is severe, spreading to the arm/jaw, or with breathlessness, call {em}."))
    if s & {"face_drooping", "slurred_speech", "one_sided_weakness"}:
        flags.append(_flag("stroke", "emergency", "Possible stroke warning signs (F.A.S.T.)",
                           f"Face drooping, arm weakness or speech difficulty can be a stroke. Note the time and call {em} immediately."))
    if s & {"confusion", "seizure", "fainting"}:
        flags.append(_flag("neuro", "emergency", "Confusion, seizure or loss of consciousness",
                           f"These need emergency assessment. Call {em}."))
    if "stiff_neck" in s and "fever" in s and s & {"severe_headache", "headache", "light_sensitivity", "rash"}:
        flags.append(_flag("meningitis", "emergency", "Fever with stiff neck and headache",
                           f"This combination can indicate meningitis. Seek emergency care now ({em})."))
    if "shortness_of_breath" in s:
        level = "emergency" if severity == "severe" else "urgent"
        flags.append(_flag("breathing", level, "Breathing difficulty",
                           "Shortness of breath should be assessed by a doctor today; if it is severe or you cannot speak in full sentences, call "
                           f"{em}."))
    if "coughing_blood" in s or "blood_in_stool" in s:
        flags.append(_flag("bleeding", "urgent", "Blood in sputum, vomit or stool", "Please see a doctor within 24 hours, or sooner if bleeding is heavy."))
    if "bleeding_gums" in s and "fever" in s:
        flags.append(_flag("dengue_warning", "urgent", "Fever with bleeding",
                           "Bleeding gums or nose with fever can be a dengue warning sign. Get a blood test and medical review today."))
    if "persistent_vomiting" in s:
        flags.append(_flag("dehydration", "urgent", "Persistent vomiting", "Risk of dehydration - seek medical care if you cannot keep fluids down."))
    if "yellow_skin_eyes" in s:
        flags.append(_flag("jaundice", "soon", "Yellowing of skin or eyes", "Jaundice should be evaluated by a doctor within a few days, sooner if you feel very unwell."))
    if "high_fever" in s and duration_days is not None and duration_days >= 3:
        flags.append(_flag("prolonged_fever", "urgent", "High fever for 3 or more days", "A doctor should examine you and may order blood tests (e.g. for dengue, malaria or typhoid)."))
    elif "fever" in s and duration_days is not None and duration_days >= 7:
        flags.append(_flag("prolonged_fever", "soon", "Fever lasting a week or more", "Persistent fever should be investigated by a doctor."))
    if profile_ctx.get("is_pregnant") and s & {"abdominal_pain", "fever", "severe_headache", "blurred_vision", "swelling_legs", "blood_in_stool"}:
        flags.append(_flag("pregnancy", "urgent", "Symptoms during pregnancy", "Contact your obstetric care provider today about these symptoms."))
    age = profile_ctx.get("age")
    if age is not None and age >= 65 and "fever" in s:
        flags.append(_flag("older_adult_fever", "soon", "Fever in an older adult", "Older adults are at higher risk of complications; consider seeing a doctor soon."))
    if severity == "severe" and not flags:
        flags.append(_flag("severe", "urgent", "You rated your symptoms as severe", "Severe symptoms should be assessed by a doctor today."))

    lab_by_key = {l["key"]: l for l in labs}
    spo2 = lab_by_key.get("spo2")
    if spo2 and spo2["value"] < 90:
        flags.append(_flag("hypoxia", "emergency", f"Oxygen saturation {spo2['value']}%", f"Oxygen saturation below 90% is dangerous. Call {em}."))
    sbp, dbp = lab_by_key.get("bp_systolic"), lab_by_key.get("bp_diastolic")
    if (sbp and sbp["value"] >= 180) or (dbp and dbp["value"] >= 120):
        lvl = "emergency" if s & {"chest_pain", "shortness_of_breath", "one_sided_weakness", "slurred_speech", "blurred_vision", "confusion", "severe_headache"} else "urgent"
        flags.append(_flag("bp_crisis", lvl, "Very high blood pressure reading",
                           "A reading of 180/120 mmHg or higher needs prompt medical attention" + (f" - with your symptoms, call {em}." if lvl == "emergency" else ", ideally today.")))
    for lab in labs:
        if lab["status"].startswith("critical") and lab["key"] not in {"spo2", "bp_systolic", "bp_diastolic"}:
            flags.append(_flag(f"critical_{lab['key']}", "urgent", f"{lab['test']} is at a critical level ({lab['value']} {lab.get('unit') or ''})",
                               "Please contact your doctor or the laboratory today to review this result."))

    # Deduplicate by code keeping the highest level.
    best: dict[str, dict] = {}
    for f in flags:
        if f["code"] not in best or URGENCY_ORDER.index(f["level"]) > URGENCY_ORDER.index(best[f["code"]]["level"]):
            best[f["code"]] = f
    return sorted(best.values(), key=lambda f: -URGENCY_ORDER.index(f["level"]))


def urgency_from(flags: list[dict], conditions: list[dict], abnormal_labs: list[dict]) -> str:
    level = max_urgency(*(f["level"] for f in flags)) if flags else "routine"
    if level == "routine":
        if abnormal_labs or any(c["confidence"] in ("moderate", "high") for c in conditions):
            level = "soon"
    return level


URGENCY_GUIDANCE = {
    "emergency": "Seek emergency medical care now.",
    "urgent": "See a doctor within 24 hours.",
    "soon": "Book a doctor's appointment within the next few days.",
    "routine": "Monitor your symptoms; see a doctor if they persist or worsen.",
}

# --- Output sanitisation for AI-generated text --------------------------------

_DOSAGE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|µg|ml|units?|iu|tablets?|capsules?)\b", re.I)
_DEFINITIVE = re.compile(
    r"\b(you (definitely|certainly|clearly|probably|likely|do) have|you have been diagnosed|you('| a)?ve been diagnosed|you are diagnosed with|"
    r"you are suffering from|you suffer from|you are (diabetic|hypertensive|anaemic|anemic)|this confirms|i diagnose|"
    r"(your )?diagnosis is|the diagnosis is)\b", re.I)
# AI text must never reassure a patient out of seeking care that the safety rules require.
_DOWNPLAY = re.compile(
    r"\b(no need to (see|visit|consult|go to|call|seek)|(is|are|it's|it is|this is) not (a )?(serious|urgent|dangerous|an emergency)|"
    r"nothing to worry|nothing serious|(do not|don't|doesn't|does not) need (to see|a doctor|medical|to worry)|"
    r"can (safely )?wait|safe to (ignore|wait)|ignore (this|these|the) (symptom|sign)s?|unlikely to be serious)\b", re.I)
_STOP_MEDS = re.compile(r"\b(stop|discontinue|double|skip) (taking )?(your )?(medication|medicine|insulin|tablets?)\b", re.I)


def sanitize_text(text: str) -> tuple[str, list[str]]:
    """Remove sentences that give dosing instructions, tell users to change
    prescribed medicines, claim a definitive diagnosis, or downplay the need for care."""
    if not text:
        return text, []
    removed: list[str] = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept = []
    for sent in sentences:
        if _DOSAGE.search(sent) or _DEFINITIVE.search(sent) or _STOP_MEDS.search(sent) or _DOWNPLAY.search(sent):
            removed.append(sent.strip())
        else:
            kept.append(sent)
    return " ".join(kept).strip(), removed


def sanitize_payload(obj):
    """Recursively sanitise all strings in an AI JSON payload."""
    removed: list[str] = []

    def walk(x):
        if isinstance(x, str):
            t, r = sanitize_text(x)
            removed.extend(r)
            return t
        if isinstance(x, list):
            out = []
            for i in x:
                w = walk(i)
                if isinstance(w, str) and not w:
                    continue
                out.append(w)
            return out
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        return x

    return walk(obj), removed
