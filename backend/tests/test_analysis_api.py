from tests.conftest import upload


def test_symptom_catalog(client):
    cat = client.get("/api/analyses/symptoms").json()
    assert any(x["key"] == "fever" for x in cat)


def test_analysis_requires_input(client, auth):
    r = client.post("/api/analyses", headers=auth, json={})
    assert r.status_code == 422
    assert "at least one" in r.json()["detail"]


def test_analysis_unknown_report_rejected(client, auth):
    r = client.post("/api/analyses", headers=auth, json={"symptoms": ["fever"], "report_ids": [99999]})
    assert r.status_code == 422


def test_full_multimodal_analysis(client, auth):
    client.put("/api/profile", headers=auth, json={"date_of_birth": "1974-03-15", "sex": "female", "height_cm": 158, "weight_kg": 74, "activity_level": "low"})
    client.post("/api/history", headers=auth, json={"category": "condition", "title": "Family history of diabetes"})
    rep = upload(client, auth, "synthetic_metabolic_panel.pdf").json()
    img = upload(client, auth, "synthetic_grayscale_image.png", kind="image", report_type="xray").json()

    r = client.post("/api/analyses", headers=auth, json={
        "symptoms": ["fatigue", "excessive_thirst"], "symptom_text": "I urinate frequently and feel tired",
        "duration_days": 30, "severity": "mild", "report_ids": [rep["id"]], "image_ids": [img["id"]],
    })
    assert r.status_code == 201, r.text
    a = r.json()
    res = a["result"]
    assert a["is_mock"] is True and a["provider"] == "mock"
    assert res["conditions"][0]["key"] == "type_2_diabetes"
    assert res["conditions"][0]["confidence"] == "high"
    keys = {c["key"] for c in res["conditions"]}
    assert "hyperlipidaemia" in keys and "hypertension" in keys
    factor_types = {f["type"] for f in res["conditions"][0]["factors"]}
    assert {"symptom", "lab", "risk_factor"} <= factor_types
    assert res["urgency"] in ("soon", "urgent")
    assert "not a medical diagnosis" in res["disclaimer"]
    assert res["sources"] and all(s["source"] in ("WHO", "CDC") for s in res["sources"])
    assert res["care_plan"]["suggested_tests"]
    assert any("BMI" in p for p in res["care_plan"]["personalised"])
    assert "Mock AI mode" in res["explanation"]["notice"]
    assert res["images"][0]["ai_observation"]["is_mock"] is True
    assert any("quality only" in l for l in res["limitations"])

    listed = client.get("/api/analyses", headers=auth).json()
    assert listed[0]["id"] == a["id"] and listed[0]["top_condition"]
    assert client.get(f"/api/analyses/{a['id']}", headers=auth).status_code == 200
    assert client.delete(f"/api/analyses/{a['id']}", headers=auth).status_code == 204


def test_emergency_analysis(client, auth):
    r = client.post("/api/analyses", headers=auth, json={"symptom_text": "crushing chest pain, sweating and short of breath", "severity": "severe"})
    res = r.json()["result"]
    assert res["urgency"] == "emergency"
    assert res["explanation"]["summary"].startswith("Seek emergency")
    assert res["care_plan"]["follow_up"].startswith("Now")


def test_knowledge_search(client, auth):
    r = client.get("/api/knowledge/search", headers=auth, params={"q": "dengue platelets bleeding"})
    assert r.status_code == 200
    assert r.json()["results"][0]["source"] in ("WHO", "CDC")
    assert "dengue" in r.json()["results"][0]["title"].lower()
