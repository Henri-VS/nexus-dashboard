def test_healthz_returns_200(client):
    r = client.get("/healthz")
    assert r.status_code == 200


def test_healthz_has_status_field(client):
    r = client.get("/healthz")
    data = r.json()
    assert "status" in data
    assert data["status"] == "ok"


def test_healthz_has_auth_enabled_field(client):
    r = client.get("/healthz")
    data = r.json()
    assert "auth_enabled" in data
    assert data["auth_enabled"] is True
