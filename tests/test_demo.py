"""Browser demo tests."""
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_demo_page_loads():
    response = client.get("/demo")

    assert response.status_code == 200
    assert "Outbound Follow-Up Agent" in response.text


def test_demo_run_estimate_returns_preview():
    response = client.post("/demo/run", json={
        "campaign_type": "estimate_followup",
        "name": "Jane Doe",
        "phone": "+15551234567",
        "service_context": "Pending AC estimate",
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload["demo_mode"] is True
    assert payload["previews"][0]["label"] == "SMS preview"


def test_demo_run_seasonal_returns_voice_preview():
    response = client.post("/demo/run", json={
        "campaign_type": "seasonal",
        "name": "Jane Doe",
        "phone": "+15551234567",
        "service_context": "HVAC seasonal tune-up",
    })

    assert response.status_code == 200
    assert response.json()["previews"][0]["label"] == "Outbound voice call preview"
