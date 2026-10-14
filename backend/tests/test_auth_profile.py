from datetime import date


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    st = client.get("/api/system/status").json()
    assert st["ai"]["mock_mode"] is True
    assert "not a medical diagnosis" in st["disclaimer"]


def test_register_login_me(client):
    body = {"email": "Alice@Example.com", "full_name": "Alice", "password": "Secret123"}
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "alice@example.com"
    assert client.post("/api/auth/register", json=body).status_code == 409

    bad = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrongpass1"})
    assert bad.status_code == 401
    ok = client.post("/api/auth/login", json={"email": "ALICE@example.com", "password": "Secret123"})
    assert ok.status_code == 200
    token = ok.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["full_name"] == "Alice"


def test_password_rules_and_validation_message(client):
    r = client.post("/api/auth/register", json={"email": "b@example.com", "full_name": "Bob", "password": "allletters"})
    assert r.status_code == 422
    assert "letter and one number" in r.json()["detail"]


def test_requires_auth(client):
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/profile", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_profile_update_and_derived_fields(client, auth):
    r = client.put("/api/profile", headers=auth, json={
        "date_of_birth": "1990-01-01", "sex": "male", "height_cm": 175, "weight_kg": 70,
        "is_pregnant": True, "allergies": ["Peanuts", " peanuts ", ""], "smoker": True,
    })
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["bmi"] == 22.9
    assert p["age"] >= 36
    assert p["is_pregnant"] is False  # only applies to female profiles
    assert p["allergies"] == ["Peanuts"]


def test_profile_rejects_future_dob(client, auth):
    future = date(date.today().year + 1, 1, 1).isoformat()
    r = client.put("/api/profile", headers=auth, json={"date_of_birth": future})
    assert r.status_code == 422


def test_history_crud_and_isolation(client, auth):
    r = client.post("/api/history", headers=auth, json={"category": "condition", "title": "Asthma", "is_ongoing": True})
    assert r.status_code == 201
    eid = r.json()["id"]
    r = client.patch(f"/api/history/{eid}", headers=auth, json={"details": "Childhood onset"})
    assert r.json()["details"] == "Childhood onset"
    assert len(client.get("/api/history", headers=auth).json()) == 1

    other = client.post("/api/auth/register", json={"email": "eve@example.com", "full_name": "Eve", "password": "Password1"}).json()
    eh = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get("/api/history", headers=eh).json() == []
    assert client.delete(f"/api/history/{eid}", headers=eh).status_code == 404

    assert client.delete(f"/api/history/{eid}", headers=auth).status_code == 204
    assert client.get("/api/history", headers=auth).json() == []
