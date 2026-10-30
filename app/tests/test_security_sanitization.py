"""Tests for input sanitization and API authentication security."""

from config import settings
from middleware.sanitization import sanitize_text


def test_sanitize_text_strips_scripts():
    malicious = "Title <script>alert('xss')</script> Clean"
    sanitized = sanitize_text(malicious)
    assert "<script>" not in sanitized
    assert "alert('xss')" not in sanitized
    assert "Title" in sanitized


def test_create_task_sanitizes_payload(client):
    payload = {
        "title": "Fix security <script>evil()</script>",
        "description": "Details <iframe src='malicious.com'></iframe>safe",
    }
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "<script>" not in data["title"]
    assert "<iframe" not in data["description"]
    assert "Fix security" in data["title"]


def test_authentication_enforcement_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "api_key", "secret-token-12345")

    # Unauthorized request without headers
    unauth_resp = client.post("/tasks", json={"title": "Protected Task"})
    assert unauth_resp.status_code == 401

    # Authorized request with API Key
    auth_resp = client.post(
        "/tasks",
        json={"title": "Protected Task"},
        headers={"X-API-Key": "secret-token-12345"},
    )
    assert auth_resp.status_code == 201
