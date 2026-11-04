import pytest


@pytest.mark.django_db
def test_liveness_is_public(api_client):
    resp = api_client.get("/api/v1/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_reports_booleans_only(api_client):
    resp = api_client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "checks": {"database": True}}


@pytest.mark.django_db
def test_request_id_is_echoed_when_safe(api_client):
    resp = api_client.get("/api/v1/health/live", HTTP_X_REQUEST_ID="abcdef12-3456")
    assert resp["X-Request-ID"] == "abcdef12-3456"


@pytest.mark.django_db
def test_request_id_is_regenerated_when_unsafe(api_client):
    resp = api_client.get("/api/v1/health/live", HTTP_X_REQUEST_ID="bad\nINJECTED log line")
    assert "\n" not in resp["X-Request-ID"]
    assert resp["X-Request-ID"] != "bad\nINJECTED log line"
