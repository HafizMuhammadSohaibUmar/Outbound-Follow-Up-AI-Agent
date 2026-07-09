"""Request security helpers."""
from fastapi import Header, HTTPException, Request
from twilio.request_validator import RequestValidator

from config import get_settings


async def require_admin_key(x_leadpilot_key: str = Header(default="")) -> None:
    settings = get_settings()
    if not settings.campaign_admin_api_key or x_leadpilot_key != settings.campaign_admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin API key")


async def validate_twilio_form(request: Request) -> dict:
    settings = get_settings()
    form = dict(await request.form())
    if not settings.validate_twilio_signature:
        return form
    signature = request.headers.get("X-Twilio-Signature", "")
    url = settings.public_base_url.rstrip("/") + request.url.path
    if request.url.query:
        url += "?" + request.url.query
    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(url, form, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    return form
