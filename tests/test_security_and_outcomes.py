"""Admin security and reply outcome tests."""
from fastapi.testclient import TestClient

from main import app
from services.outcome import classify_reply

client = TestClient(app)


def test_admin_run_requires_api_key():
    response = client.post("/campaigns/estimate_followup/run")

    assert response.status_code == 403


def test_admin_run_accepts_api_key():
    response = client.post(
        "/campaigns/estimate_followup/run",
        headers={"X-LeadPilot-Key": "test-admin-key"},
    )

    assert response.status_code == 200


def test_reply_classifier():
    assert classify_reply("STOP") == "stop"
    assert classify_reply("yes please schedule") == "accepted"
    assert classify_reply("too expensive right now") == "declined"
    assert classify_reply("Can you explain the warranty?") == "needs_followup"


def test_sms_reply_endpoint_uses_twilio_form():
    response = client.post(
        "/twilio/sms-reply",
        data={"From": "+15551234567", "Body": "STOP", "MessageSid": "SM1"},
    )

    assert response.status_code == 200
    assert response.headers["X-LeadPilot-Status"] == "suppressed"
