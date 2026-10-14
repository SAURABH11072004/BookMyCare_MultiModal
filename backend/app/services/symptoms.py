"""Symptom vocabulary and free-text symptom extraction (keyword/synonym based)."""
from __future__ import annotations

import re

# key -> (display label, synonyms/phrases matched in free text)
SYMPTOMS: dict[str, tuple[str, tuple[str, ...]]] = {
    "fever": ("Fever", ("fever", "feverish", "high temperature", "temperature", "bukhar", "pyrexia")),
    "high_fever": ("High fever (≥39 °C / 102 °F)", ("high fever", "very high fever", "fever of 103", "fever of 104", "102 f", "103 f", "104 f")),
    "chills": ("Chills / shivering", ("chills", "shivering", "rigors", "shaking chills")),
    "cough": ("Cough", ("cough", "coughing")),
    "dry_cough": ("Dry cough", ("dry cough",)),
    "productive_cough": ("Cough with phlegm", ("phlegm", "sputum", "mucus cough", "wet cough", "productive cough")),
    "coughing_blood": ("Coughing up blood", ("coughing blood", "coughing up blood", "blood in sputum", "haemoptysis", "hemoptysis")),
    "sore_throat": ("Sore throat", ("sore throat", "throat pain", "painful swallowing")),
    "runny_nose": ("Runny or blocked nose", ("runny nose", "blocked nose", "stuffy nose", "nasal congestion", "congestion")),
    "sneezing": ("Sneezing", ("sneezing", "sneeze")),
    "headache": ("Headache", ("headache", "head ache", "head pain")),
    "severe_headache": ("Sudden or severe headache", ("severe headache", "worst headache", "sudden headache", "thunderclap")),
    "eye_pain": ("Pain behind the eyes", ("pain behind the eyes", "pain behind eyes", "retro-orbital", "eye pain")),
    "light_sensitivity": ("Sensitivity to light", ("sensitive to light", "light sensitivity", "photophobia")),
    "body_aches": ("Body / muscle aches", ("body ache", "body aches", "muscle ache", "muscle pain", "myalgia", "body pain")),
    "joint_pain": ("Joint pain", ("joint pain", "joints hurt", "arthralgia")),
    "fatigue": ("Fatigue / tiredness", ("fatigue", "tired", "tiredness", "weakness", "exhausted", "lethargy", "low energy")),
    "shortness_of_breath": ("Shortness of breath", ("shortness of breath", "breathless", "breathlessness", "difficulty breathing", "short of breath", "can't breathe", "cannot breathe", "trouble breathing")),
    "wheezing": ("Wheezing", ("wheeze", "wheezing", "whistling breath")),
    "chest_tightness": ("Chest tightness", ("chest tightness", "tight chest")),
    "chest_pain": ("Chest pain or pressure", ("chest pain", "chest pressure", "pain in chest", "crushing chest")),
    "palpitations": ("Palpitations", ("palpitations", "racing heart", "heart pounding", "fluttering heart")),
    "sweating": ("Cold sweat / heavy sweating", ("cold sweat", "sweating", "diaphoresis")),
    "night_sweats": ("Night sweats", ("night sweats", "sweating at night")),
    "nausea": ("Nausea", ("nausea", "nauseous", "queasy", "feel sick")),
    "vomiting": ("Vomiting", ("vomiting", "vomit", "throwing up", "threw up")),
    "persistent_vomiting": ("Persistent vomiting", ("persistent vomiting", "can't keep anything down", "vomiting repeatedly", "continuous vomiting")),
    "diarrhea": ("Diarrhoea", ("diarrhea", "diarrhoea", "loose stools", "loose motions", "watery stools")),
    "constipation": ("Constipation", ("constipation", "constipated")),
    "abdominal_pain": ("Abdominal pain", ("abdominal pain", "stomach pain", "stomach ache", "belly pain", "tummy pain", "abdomen pain", "cramps")),
    "loss_of_appetite": ("Loss of appetite", ("loss of appetite", "no appetite", "not hungry", "poor appetite")),
    "loss_of_taste_smell": ("Loss of taste or smell", ("loss of taste", "loss of smell", "can't smell", "can't taste", "anosmia")),
    "rash": ("Skin rash", ("rash", "red spots", "skin eruption")),
    "itching": ("Itching", ("itching", "itchy", "pruritus")),
    "excessive_thirst": ("Excessive thirst", ("excessive thirst", "very thirsty", "always thirsty", "polydipsia")),
    "frequent_urination": ("Frequent urination", ("frequent urination", "urinating often", "peeing a lot", "polyuria", "urinate frequently")),
    "burning_urination": ("Burning or painful urination", ("burning urination", "burning while urinating", "painful urination", "dysuria", "burning when i pee")),
    "blurred_vision": ("Blurred vision", ("blurred vision", "blurry vision")),
    "slow_healing": ("Slow-healing sores", ("slow healing", "wounds not healing", "sores that heal slowly")),
    "numbness_tingling": ("Numbness / tingling in hands or feet", ("numbness", "tingling", "pins and needles")),
    "weight_loss": ("Unexplained weight loss", ("weight loss", "losing weight", "lost weight")),
    "weight_gain": ("Unexplained weight gain", ("weight gain", "gaining weight", "gained weight")),
    "dizziness": ("Dizziness / light-headedness", ("dizziness", "dizzy", "light-headed", "lightheaded", "vertigo")),
    "pale_skin": ("Pale skin", ("pale skin", "pallor", "looking pale", "pale")),
    "cold_intolerance": ("Feeling cold easily", ("cold intolerance", "always cold", "feel cold")),
    "dry_skin": ("Dry skin", ("dry skin",)),
    "hair_loss": ("Hair loss / thinning", ("hair loss", "hair fall", "thinning hair")),
    "swelling_legs": ("Swelling of legs / ankles", ("swollen legs", "swollen ankles", "leg swelling", "ankle swelling", "edema", "oedema", "puffy feet")),
    "yellow_skin_eyes": ("Yellowing of skin or eyes", ("jaundice", "yellow eyes", "yellow skin", "yellowing")),
    "dark_urine": ("Dark urine", ("dark urine", "cola coloured urine", "brown urine")),
    "flank_pain": ("Back / side (flank) pain", ("flank pain", "side pain", "kidney pain", "lower back pain")),
    "bleeding_gums": ("Bleeding gums or nose", ("bleeding gums", "nosebleed", "nose bleed", "gum bleeding")),
    "bone_pain": ("Bone or muscle weakness", ("bone pain", "muscle weakness", "aching bones")),
    "low_mood": ("Low mood / loss of interest", ("low mood", "depressed", "sad all the time", "hopeless", "no interest", "loss of interest")),
    "sleep_problems": ("Sleep problems", ("insomnia", "can't sleep", "trouble sleeping", "poor sleep")),
    "confusion": ("Confusion", ("confusion", "confused", "disoriented")),
    "fainting": ("Fainting / loss of consciousness", ("fainted", "fainting", "passed out", "unconscious", "blackout")),
    "seizure": ("Seizure", ("seizure", "seizures", "convulsion", "convulsions")),
    "stiff_neck": ("Stiff neck", ("stiff neck", "neck stiffness")),
    "face_drooping": ("Face drooping", ("face drooping", "facial droop", "drooping face", "face droop")),
    "slurred_speech": ("Slurred speech / trouble speaking", ("slurred speech", "trouble speaking", "can't speak", "difficulty speaking")),
    "one_sided_weakness": ("Weakness on one side of the body", ("one sided weakness", "weakness on one side", "arm weakness", "can't move my arm", "paralysis")),
    "blood_in_stool": ("Blood in stool or vomit", ("blood in stool", "bloody stool", "blood in vomit", "black stool", "vomiting blood")),
    "self_harm_thoughts": ("Thoughts of self-harm or suicide", ("suicide", "suicidal", "kill myself", "end my life", "want to die", "self harm", "self-harm", "hurt myself")),
}

LABELS = {k: v[0] for k, v in SYMPTOMS.items()}

_PATTERNS = [
    (key, re.compile(r"(?<![a-z])" + re.escape(phrase).replace(r"\ ", r"\s+") + r"(?![a-z])", re.I))
    for key, (_label, phrases) in SYMPTOMS.items()
    for phrase in phrases
]
_NEGATION = re.compile(r"\b(no|not|without|denies|never|don't have|do not have)\b[^.,;]{0,25}$", re.I)


def extract_symptoms(text: str | None) -> list[str]:
    """Find symptom keys mentioned in free text, skipping simple negations
    such as "no fever"."""
    if not text:
        return []
    found: list[str] = []
    for key, rx in _PATTERNS:
        for m in rx.finditer(text):
            prefix = text[max(0, m.start() - 40): m.start()]
            if _NEGATION.search(prefix):
                continue
            if key not in found:
                found.append(key)
            break
    return found


def normalise(selected: list[str], text: str | None) -> list[str]:
    """Merge explicitly selected symptoms (keys or free labels) with symptoms
    extracted from free text. Unknown entries are matched via extraction."""
    keys: list[str] = []
    for item in selected:
        k = item.strip().lower().replace(" ", "_")
        if k in SYMPTOMS:
            keys.append(k)
        else:
            keys.extend(extract_symptoms(item))
    keys.extend(extract_symptoms(text))
    # implied parents
    if "high_fever" in keys:
        keys.append("fever")
    if "dry_cough" in keys or "productive_cough" in keys or "coughing_blood" in keys:
        keys.append("cough")
    if "persistent_vomiting" in keys:
        keys.append("vomiting")
    if "severe_headache" in keys:
        keys.append("headache")
    out: list[str] = []
    for k in keys:
        if k not in out:
            out.append(k)
    return out
