"""Unit tests for the rule-based engine, safety layer, retrieval and providers."""
import pytest

from app.ai import registry
from app.ai.base import LLMRequest, ProviderError, parse_json_loose
from app.ai.mock import MockProvider
from app.services import safety
from app.services.lab_parser import classify, parse_lab_values, SPEC_BY_KEY
from app.services.retrieval import BM25Index
from app.services.scoring import load_conditions, score_conditions
from app.services.symptoms import SYMPTOMS, extract_symptoms, normalise


# --- symptoms ---------------------------------------------------------------
def test_symptom_extraction_with_negation():
    keys = extract_symptoms("I have had a high fever and joint pain, no cough, and pain behind the eyes")
    assert {"high_fever", "joint_pain", "eye_pain"} <= set(keys)
    assert "cough" not in keys


def test_normalise_adds_parent_symptoms():
    keys = normalise(["high_fever", "Dry cough"], None)
    assert {"fever", "cough", "dry_cough", "high_fever"} <= set(keys)


def test_knowledge_base_references_valid_keys():
    for c in load_conditions():
        for s in c["symptoms"]:
            assert s in SYMPTOMS, (c["key"], s)
        for k in c.get("key_symptoms", []):
            assert k in SYMPTOMS, (c["key"], k)
        for lab in c["labs"]:
            assert lab["key"] in SPEC_BY_KEY, (c["key"], lab["key"])


# --- labs ---------------------------------------------------------------------
@pytest.mark.parametrize("text,key,value,status", [
    ("Hemoglobin: 10.8 g/dL (12.0 - 15.5)", "hemoglobin", 10.8, "low"),
    ("HbA1c 7.1 %", "hba1c", 7.1, "high"),
    ("Fasting Blood Sugar - 92 mg/dL", "glucose_fasting", 92, "normal"),
    ("Platelet count 42,000 /cumm", "platelets", 42, "critical_low"),
    ("TSH (3rd gen) 8.4 mIU/L", "tsh", 8.4, "high"),
])
def test_lab_parsing(text, key, value, status):
    vals = {v["key"]: v for v in parse_lab_values(text)}
    assert vals[key]["value"] == value
    assert vals[key]["status"] == status


def test_sex_specific_ranges():
    spec = SPEC_BY_KEY["hemoglobin"]
    assert classify(spec, 13.0, "male") == "low"
    assert classify(spec, 13.0, "female") == "normal"


def test_label_and_value_on_separate_lines():
    vals = {v["key"]: v for v in parse_lab_values("Hemoglobin:\n9.1 g/dL\nWBC Count:\n12.5")}
    assert vals["hemoglobin"]["status"] == "low"
    assert vals["wbc"]["status"] == "high"


# --- scoring ---------------------------------------------------------------
def _top(conds):
    return conds[0]["key"] if conds else None


def test_dengue_pattern_ranks_dengue_first():
    labs = parse_lab_values("Platelets 85\nWBC 3.1")
    conds = score_conditions(["fever", "high_fever", "eye_pain", "joint_pain", "rash"], labs, {}, duration_days=3)
    assert _top(conds) == "dengue"
    top = conds[0]
    assert top["confidence"] == "high"
    assert any(f["type"] == "lab" for f in top["factors"])
    assert abs(sum(f["share"] for f in top["factors"]) - 1) < 0.01


def test_lab_only_diabetes_detection_and_normal_lab_evidence_against():
    high = score_conditions([], parse_lab_values("HbA1c 7.4%\nFasting glucose 140"), {})
    assert _top(high) == "type_2_diabetes"
    normal = score_conditions(["excessive_thirst", "frequent_urination"], parse_lab_values("HbA1c 5.1%"), {})
    diab = next((c for c in normal if c["key"] == "type_2_diabetes"), None)
    assert diab is None or any(f["direction"] == "against" for f in diab["factors"])


def test_requires_lab_confirmation_caps_score():
    conds = score_conditions(["excessive_thirst", "frequent_urination", "blurred_vision", "slow_healing"], [], {"bmi": 32, "age": 50})
    diab = next(c for c in conds if c["key"] == "type_2_diabetes")
    assert diab["match_score"] <= 0.45
    assert diab["notes"]


def test_risk_factors_alone_do_not_create_matches():
    assert score_conditions([], [], {"age": 70, "bmi": 35, "smoker": True}) == []


def test_duration_supports_tb():
    short = score_conditions(["cough", "night_sweats", "weight_loss"], [], {}, duration_days=3)
    long = score_conditions(["cough", "night_sweats", "weight_loss"], [], {}, duration_days=21)
    s = next(c for c in short if c["key"] == "tuberculosis")["match_score"]
    l = next(c for c in long if c["key"] == "tuberculosis")["match_score"]
    assert l > s


# --- safety -------------------------------------------------------------------
def test_red_flags_emergency_for_cardiac_and_stroke():
    flags = safety.detect_red_flags(["chest_pain", "sweating"], [], {})
    assert flags[0]["level"] == "emergency" and flags[0]["code"] == "cardiac"
    flags = safety.detect_red_flags(["face_drooping"], [], {})
    assert flags[0]["code"] == "stroke"


def test_self_harm_flag_shows_crisis_line():
    flags = safety.detect_red_flags(normalise([], "I feel hopeless and want to die"), [], {})
    f = next(f for f in flags if f["code"] == "self_harm")
    assert f["level"] == "emergency" and "14416" in f["message"]


def test_critical_lab_and_bp_crisis():
    labs = parse_lab_values("BP 190/125 mmHg\nPotassium 7.1")
    codes = {f["code"]: f for f in safety.detect_red_flags([], labs, {})}
    assert codes["bp_crisis"]["level"] == "urgent"
    assert "critical_potassium" in codes


def test_urgency_routine_when_nothing_found():
    assert safety.urgency_from([], [], []) == "routine"


def test_sanitizer_removes_doses_and_diagnoses():
    text = "Rest well. Take 500 mg paracetamol every 6 hours. You definitely have dengue. Drink fluids."
    clean, removed = safety.sanitize_text(text)
    assert clean == "Rest well. Drink fluids."
    assert len(removed) == 2
    payload, removed = safety.sanitize_payload({"q": ["Stop taking your medication now.", "Ask about tests."]})
    assert payload["q"] == ["Ask about tests."] and len(removed) == 1


# --- retrieval ------------------------------------------------------------------
def test_bm25_ranks_relevant_document():
    docs = [
        {"title": "Dengue", "content": "Dengue causes fever, pain behind the eyes and low platelets.", "topics": ["dengue"]},
        {"title": "Diabetes", "content": "Diabetes is raised blood sugar. HbA1c measures it.", "topics": ["type_2_diabetes"]},
    ]
    idx = BM25Index(docs)
    assert idx.search("blood sugar hba1c")[0][0]["title"] == "Diabetes"
    assert idx.search("platelets fever")[0][0]["title"] == "Dengue"
    assert idx.search("unrelated", topics=["dengue"])[0][0]["title"] == "Dengue"


# --- providers --------------------------------------------------------------------
def test_parse_json_loose():
    assert parse_json_loose('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_loose('Sure! {"a": 2} hope it helps') == {"a": 2}
    assert parse_json_loose("no json") is None


def test_force_mock_uses_mock_provider():
    chain = registry.provider_chain()
    assert [p.name for p in chain] == ["mock"]


def test_fallback_to_mock_when_provider_fails(monkeypatch):
    class Broken(MockProvider):
        name = "broken"
        is_mock = False

        def _generate(self, req):
            raise ProviderError("HTTP 500")

    monkeypatch.setattr(registry, "provider_chain", lambda need_vision=False: [Broken(), MockProvider()])
    out = registry.generate(LLMRequest(task="analysis_explanation", system="s", prompt="p", context={"urgency": "routine"}))
    assert out.response.provider == "mock"
    assert out.fell_back and out.attempts[0]["error"] == "HTTP 500"


def test_remote_provider_selected_when_key_present(monkeypatch):
    from app.core.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "ai_force_mock", False)
    monkeypatch.setattr(s, "groq_api_key", "test-key")
    monkeypatch.setattr(s, "gemini_api_key", "")
    names = [p.name for p in registry.provider_chain()]
    assert names == ["groq", "mock"]
    # Groq is text-only, so an image request skips it.
    assert [p.name for p in registry.provider_chain(need_vision=True)] == ["mock"]


def test_mock_output_is_labelled():
    resp = MockProvider().generate(LLMRequest(task="analysis_explanation", system="", prompt="", context={
        "urgency": "soon", "conditions": [{"name": "Dengue fever", "match_score": 0.8, "confidence": "high"}],
        "abnormal_labs": [], "symptom_labels": ["Fever"]}))
    assert resp.is_mock and "Mock AI mode" in resp.data["notice"]
