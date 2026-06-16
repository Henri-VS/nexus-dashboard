"""One smoke test per router: no-auth → 401; with auth → not 500."""
import pytest
from tests.conftest import AUTH

# (path, method) pairs — one per router
ENDPOINTS = [
    ("/api/weather/current",        "GET"),
    ("/api/system/stats",           "GET"),
    ("/api/security/alerts",        "GET"),
    ("/api/docker/containers",      "GET"),
    ("/api/notes/recent",           "GET"),
    ("/api/home/entities",          "GET"),
    ("/api/learn/progress",         "GET"),
    ("/api/ai/health",              "GET"),
    ("/api/calendar/events",        "GET"),
    ("/api/news",                   "GET"),
    ("/api/quicklinks",             "GET"),
    ("/api/heartbeat/status",       "GET"),
    ("/api/logs",                   "GET"),
    ("/api/automations",            "GET"),
    ("/api/notifications/config",   "GET"),
    ("/api/nexus/config",           "GET"),
    ("/api/rag/status",             "GET"),
    ("/api/services",               "GET"),
]


@pytest.mark.parametrize("path,method", ENDPOINTS)
def test_no_auth_returns_401(client, path, method):
    r = client.request(method, path)
    assert r.status_code == 401, f"{method} {path} should be 401 without auth, got {r.status_code}"


@pytest.mark.parametrize("path,method", ENDPOINTS)
def test_with_auth_not_500(client, path, method):
    r = client.request(method, path, headers=AUTH)
    assert r.status_code != 500, f"{method} {path} returned 500: {r.text}"
    # Endpoint should return valid JSON
    r.json()
