"""Evidence-grounded AI assessment workflow.

The HTTP layer of the AI providers is stubbed (no network, no real keys), but
everything else - scoring, safety rules, retrieval, citation validation, output
sanitising and the structured assessment - runs for real.
"""
from __future__ import annotations

import json

import httpx
import pytest

from app.ai import remote
from app.ai.base import ProviderError
from app.core.config import Settings, get_settings
from app.services import grounding
from app.services.safety import sanitize_text
from tests.conftest import upload

DENGUE_TEXT = "high fever, pain behind the eyes, body aches and a rash"


def gemini_reply(obj) -> dict:
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def groq_reply(obj) -> dict:
    return {"choices": [{"message": {"content": obj if isinstance(obj, str) else json.dumps(obj)}}]}


GOOD = {
    "summary": "Your symptoms may be consistent with a viral illness that a doctor can confirm with tests.",
    "report_interpretation": "",
    "condition_notes": [],
    "uncertainty": ["A blood test is needed to tell these apart."],
    "questions_for_doctor": ["Which tests should I have?"],
}


@pytest.fixture
def live(monkeypatch):
    """Real-provider mode with a stubbed HTTP layer. Set ``live.handlers['gemini'|'groq']``."""
    s = get_settings()
    monkeypatch.setattr(s, "ai_force_mock", False)
    monkeypatch.setattr(s, "gemini_api_key", "g-key")
    monkeypatch.setattr(s, "groq_api_key", "")
    monkeypatch.setattr(s, "openrouter_api_key", "")
    monkeypatch.setattr(s, "ai_allow_mock_fallback", True)

    class Live:
        calls: list[tuple[str, dict]] = []
        handlers: dict = {"gemini": lambda p: gemini_reply(GOOD), "groq": lambda p: groq_reply(GOOD)}

        def prompts(self, host="gemini"):
            out = []
            for url, payload in self.calls:
                if host in url:
                    out.append(payload["contents"][0]["parts"][0]["text"] if host == "generativelanguage" or "contents" in payload
                               else payload["messages"][1]["content"])
            return out

    live = Live()
    live.calls = []

    def fake_post(url, headers, payload):
        live.calls.append((url, payload))
        host = "gemini" if "googleapis" in url else "groq"
        h = live.handlers[host]
        if isinstance(h, Exception):
            raise h
        return h(payload)

    monkeypatch.setattr(remote, "_post", fake_post)
    live.settings = s
    return live


def analyse(client, auth, **body):
    r = client.post("/api/analyses", headers=auth, json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ------------------------------------------------------------------ grounded output + citations

def test_grounded_response_uses_only_real_citations_and_cannot_diagnose(client, auth, live):
    client.put("/api/profile", headers=auth, json={"date_of_birth": "1995-05-05", "sex": "male", "chronic_conditions": ["Asthma"]})
    live.handlers["gemini"] = lambda p: gemini_reply({
        "summary": "You have dengue. Fever with eye pain may be consistent with an infection (see [S1] and [S99]).",
        "report_interpretation": "",
        "condition_notes": [
            {"key": "dengue", "explanation": "Fever and pain behind the eyes can fit dengue; a doctor can confirm.", "cites": ["S1", "S99"]},
            {"key": "made_up_disease", "explanation": "Invented.", "cites": ["S1"]},
            {"key": "influenza", "explanation": "Flu is also possible.", "cites": []},
        ],
        "uncertainty": ["Only a blood test can separate these."],
        "questions_for_doctor": ["Do I need a dengue test?"],
    })
    a = analyse(client, auth, symptom_text=DENGUE_TEXT, duration_days=4)
    res = a["result"]

    assert res["ai"]["status"] == "generated" and res["ai"]["is_real_ai"] is True
    assert a["is_mock"] is False and a["provider"] == "gemini" and res["is_mock"] is False
    assert "Mock AI mode" not in (res["explanation"]["notice"] or "")

    # every citation is a genuine WHO/CDC passage from the knowledge base
    cites = res["assessment"]["citations"]
    assert cites and [c["id"] for c in cites] == [f"S{i}" for i in range(1, len(cites) + 1)]
    assert all(c["url"].startswith(("https://www.who.int", "https://www.cdc.gov")) for c in cites)
    # invented citation ids / conditions / assertions were removed
    summary = res["explanation"]["summary"]
    assert "[S99]" not in summary and "You have dengue" not in summary
    assert summary.startswith("See a doctor within 24 hours.")  # safety rules speak first
    assert res["explanation"]["safety_filtered_sentences"] >= 1
    notes = {n["key"]: n for n in res["explanation"]["condition_notes"]}
    assert "made_up_disease" not in notes
    assert notes["dengue"]["cites"] == ["S1"] and notes["dengue"]["grounded"] is True
    assert notes["influenza"]["grounded"] is False

    dengue = next(c for c in res["assessment"]["possible_conditions"] if c["key"] == "dengue")
    assert dengue["status"] == "unconfirmed" and dengue["is_diagnosis"] is False
    assert dengue["evidence_ids"] and dengue["ai_grounded"] is True
    src = {c["id"]: c for c in cites}
    assert any("dengue" in (src[i]["title"].lower()) for i in dengue["evidence_ids"])
    assert res["assessment"]["diagnosis_status"] == "screening_only_not_a_diagnosis"

    # the model was given numbered passages and the patient's history
    prompt = live.prompts()[0]
    assert '"S1"' in prompt and "Asthma" in prompt and "WHO" in prompt


def test_prompt_contains_history_labs_and_known_condition_flag(client, auth, live):
    client.put("/api/profile", headers=auth, json={
        "date_of_birth": "1974-03-15", "sex": "female", "height_cm": 158, "weight_kg": 74, "chronic_conditions": ["Type 2 diabetes"],
    })
    rep = upload(client, auth, "synthetic_metabolic_panel.pdf").json()
    a = analyse(client, auth, symptoms=["excessive_thirst", "frequent_urination", "fatigue"], symptom_text="", report_ids=[rep["id"]], duration_days=30)
    res = a["result"]
    top = res["assessment"]["possible_conditions"][0]
    assert top["key"] == "type_2_diabetes" and top["already_in_history"] is True
    assert any("diabetes" in h.lower() for h in top["history_considered"])
    assert any("already listed" in u for u in top["uncertainty"])
    assert any(l["type"] == "lab" for l in top["supporting"])
    # evidence retrieved because of the patient's own history
    assert any(r.startswith("history:") for c in res["assessment"]["citations"] for r in c["reasons"])
    assert res["assessment"]["history_considered"]["conditions"] == ["Type 2 diabetes"]
    prompt = live.prompts()[0]
    assert "Type 2 diabetes" in prompt and '"already_in_patient_history": true' in prompt and "HbA1c" in prompt


# ------------------------------------------------------------------ safety

def test_model_cannot_change_urgency_or_downplay(client, auth, live):
    live.handlers["gemini"] = lambda p: gemini_reply({
        "urgency": "routine",
        "summary": "There is no need to see a doctor. This is not serious. Your symptoms may be consistent with a viral illness.",
        "condition_notes": [], "uncertainty": [], "questions_for_doctor": [],
    })
    res = analyse(client, auth, symptom_text=DENGUE_TEXT, duration_days=4)["result"]
    assert res["urgency"] == "urgent" and res["assessment"]["urgency"]["set_by"] == "safety_rules"
    assert any(f["code"] == "prolonged_fever" for f in res["red_flags"])
    s = res["explanation"]["summary"]
    assert s.startswith("See a doctor within 24 hours.")
    assert "no need to see" not in s.lower() and "not serious" not in s.lower()


@pytest.mark.parametrize("text,kw", [
    ("crushing chest pain, sweating and short of breath", {"severity": "severe"}),
    ("I want to die", {}),
    ("face drooping and slurred speech", {}),
])
def test_emergencies_never_reach_the_language_model(client, auth, live, text, kw):
    live.handlers["gemini"] = lambda p: (_ for _ in ()).throw(AssertionError("model must not be called for emergencies"))
    a = analyse(client, auth, symptom_text=text, **kw)
    res = a["result"]
    assert res["urgency"] == "emergency" and res["red_flags"]
    assert res["ai"]["status"] == "skipped_emergency" and res["ai"]["is_real_ai"] is False
    assert a["is_mock"] is False and a["provider"] == "rules"
    assert res["explanation"]["summary"].startswith("Seek emergency medical care now.")
    assert "No AI model was used" in res["explanation"]["notice"]
    assert not live.calls  # no provider request at all
    assert res["assessment"]["urgency"]["level"] == "emergency"


def test_sanitiser_and_assertion_filter():
    assert sanitize_text("There is no need to see a doctor. Drink water.")[0] == "Drink water."
    assert grounding.drop_condition_assertions("You have dengue. Rest well.")[0] == "Rest well."
    assert grounding.drop_condition_assertions("This is dengue.")[0] == ""
    for ok in ("You may have dengue.", "Dengue is spread by mosquitoes.", "A doctor can confirm whether this is dengue."):
        assert grounding.drop_condition_assertions(ok)[0] == ok


# ------------------------------------------------------------------ failures are explicit

def test_missing_key_is_labelled_mock_not_real_ai(client, auth, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "ai_force_mock", False)
    monkeypatch.setattr(s, "gemini_api_key", "")
    a = analyse(client, auth, symptom_text="runny nose and sneezing")
    ai = a["result"]["ai"]
    assert ai["status"] == "mock" and ai["is_real_ai"] is False and ai["reason"] == "missing_key"
    assert "GEMINI_API_KEY" in ai["message"] and a["is_mock"] is True
    assert "Mock AI mode" in a["result"]["explanation"]["notice"]


def test_mock_fallback_can_be_disabled(client, auth, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "ai_force_mock", False)
    monkeypatch.setattr(s, "gemini_api_key", "")
    monkeypatch.setattr(s, "ai_allow_mock_fallback", False)
    a = analyse(client, auth, symptom_text="runny nose and sneezing")
    res = a["result"]
    assert res["ai"]["status"] == "failed" and res["ai"]["provider"] == "none" and a["is_mock"] is False
    assert res["explanation"]["notice"].startswith("AI explanation unavailable")
    assert "Mock AI mode" not in json.dumps(res["explanation"])
    assert res["conditions"] and res["assessment"]["possible_conditions"]  # rule-based assessment still works


@pytest.mark.parametrize("failure,kind", [
    (ProviderError("HTTP 429: quota", kind="rate_limited", status_code=429), "rate_limited"),
    (ProviderError("HTTP 401: bad key", kind="auth_error", status_code=401), "auth_error"),
    (ProviderError("HTTP 404: model gone", kind="model_not_found", status_code=404), "model_not_found"),
    (ProviderError("network error: ReadTimeout (timeout)", kind="timeout"), "timeout"),
    (ProviderError("HTTP 503", kind="server_error", status_code=503), "server_error"),
])
def test_provider_failure_falls_back_to_next_provider_and_is_reported(client, auth, live, monkeypatch, failure, kind):
    monkeypatch.setattr(live.settings, "groq_api_key", "q-key")
    live.handlers["gemini"] = failure
    res = analyse(client, auth, symptom_text="runny nose and sneezing")["result"]
    assert res["ai"]["status"] == "generated" and res["ai"]["provider"] == "groq"
    first = res["ai"]["attempts"][0]
    assert first["provider"] == "gemini" and first["ok"] is False and first["kind"] == kind


def test_all_providers_failing_shows_labelled_template_with_reasons(client, auth, live):
    live.handlers["gemini"] = ProviderError("HTTP 429: quota", kind="rate_limited", status_code=429)
    a = analyse(client, auth, symptom_text="runny nose and sneezing")
    ai = a["result"]["ai"]
    assert ai["status"] == "mock" and ai["reason"] == "all_providers_failed" and a["is_mock"] is True
    assert "rate limit" in ai["message"].lower() and ai["attempts"][0]["kind"] == "rate_limited"
    assert "rate limit" in a["result"]["explanation"]["notice"].lower()


@pytest.mark.parametrize("reply", [
    "this is not json at all",
    {"report_interpretation": "x", "condition_notes": []},          # no summary
    {"summary": "ok", "condition_notes": []},                        # summary too short to be usable
    {"summary": "A long enough summary sentence here.", "condition_notes": "not a list"},
])
def test_invalid_model_responses_are_rejected_and_reported(client, auth, live, reply):
    live.handlers["gemini"] = lambda p: gemini_reply(reply)
    ai = analyse(client, auth, symptom_text="runny nose and sneezing")["result"]["ai"]
    assert ai["status"] == "mock" and ai["is_real_ai"] is False
    assert ai["attempts"][0] == {**ai["attempts"][0], "provider": "gemini", "ok": False, "kind": "invalid_response"}


def test_all_failing_without_mock_fallback_reports_failure(client, auth, live):
    live.settings.ai_allow_mock_fallback = False
    live.handlers["gemini"] = ProviderError("HTTP 429", kind="rate_limited", status_code=429)
    res = analyse(client, auth, symptom_text="runny nose and sneezing")["result"]
    assert res["ai"]["status"] == "failed" and res["ai"]["attempts"][0]["kind"] == "rate_limited"
    assert "rate limit" in res["explanation"]["notice"].lower()


# ------------------------------------------------------------------ HTTP error classification + config

@pytest.mark.parametrize("status,kind", [(429, "rate_limited"), (401, "auth_error"), (403, "auth_error"), (404, "model_not_found"),
                                         (400, "bad_request"), (500, "server_error"), (503, "server_error")])
def test_http_status_is_classified(monkeypatch, status, kind):
    class R:
        status_code = status
        text = "x"
        headers = {"retry-after": "7"} if status == 429 else {}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: R())
    with pytest.raises(ProviderError) as e:
        remote._post("https://example.invalid", {}, {})
    assert e.value.kind == kind and e.value.status_code == status
    if status == 429:
        assert e.value.retry_after == 7.0


def test_google_invalid_key_400_is_an_auth_error(monkeypatch):
    class R:
        status_code = 400
        text = '{"error": {"code": 400, "message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}}'
        headers = {}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: R())
    with pytest.raises(ProviderError) as e:
        remote._post("https://example.invalid", {}, {})
    assert e.value.kind == "auth_error"


def test_timeout_and_bad_json_are_classified(monkeypatch):
    def boom(*a, **k):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(ProviderError) as e:
        remote._post("https://example.invalid", {}, {})
    assert e.value.kind == "timeout"

    class Bad:
        status_code = 200
        text = "<html>"

        def json(self):
            raise ValueError("no json")

    monkeypatch.setattr(httpx, "post", lambda *a, **k: Bad())
    with pytest.raises(ProviderError) as e:
        remote._post("https://example.invalid", {}, {})
    assert e.value.kind == "invalid_response"


def test_default_models_are_not_the_retired_ones():
    d = Settings(_env_file=None)
    assert d.gemini_model not in ("gemini-2.0-flash", "gemini-2.0-flash-001")
    assert d.groq_model != "llama-3.3-70b-versatile"
    assert d.provider_order[0] == "gemini"


def test_gemini3_omits_temperature_and_status_reports_reason(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "gemini_api_key", "g-key")
    monkeypatch.setattr(s, "gemini_model", "gemini-3.8-flash")
    seen = {}
    monkeypatch.setattr(remote, "_post", lambda url, h, p: seen.update(payload=p) or gemini_reply(GOOD))
    from app.ai.base import LLMRequest
    remote.GeminiProvider().generate(LLMRequest(task="t", system="s", prompt="p"))
    assert "temperature" not in seen["payload"]["generationConfig"]
    monkeypatch.setattr(s, "gemini_model", "gemini-2.5-flash")
    remote.GeminiProvider().generate(LLMRequest(task="t", system="s", prompt="p"))
    assert "temperature" in seen["payload"]["generationConfig"]
    st = client.get("/api/system/status").json()["ai"]
    assert st["unavailable_reason"] == "forced_mock" and st["allow_mock_fallback"] is True


# ------------------------------------------------------------------ structured assessment (no AI needed)

def test_structured_assessment_shape(client, auth):
    res = analyse(client, auth, symptom_text=DENGUE_TEXT, duration_days=4)["result"]
    a = res["assessment"]
    assert {"ai", "urgency", "possible_conditions", "uncertainty", "limitations", "next_steps", "citations", "history_considered"} <= a.keys()
    assert a["next_steps"]["follow_up"] and a["limitations"]
    assert any(u["source"] == "rules" for u in a["uncertainty"])
    for c in a["possible_conditions"]:
        assert c["status"] == "unconfirmed" and c["is_diagnosis"] is False
        assert c["supporting"] and c["uncertainty"] and "evidence_ids" in c
        assert all(e in {x["id"] for x in a["citations"]} for e in c["evidence_ids"])
    assert res["sources"][0]["id"] == "S1"  # legacy field kept for older clients
