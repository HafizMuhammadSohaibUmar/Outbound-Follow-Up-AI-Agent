"""Twilio SMS sender."""
import logging
from typing import Optional

import httpx

from config import get_settings
from logging_utils import log_event

logger = logging.getLogger("twilio_sms")


class TwilioSmsClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_phone_number
        self.api_base = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"
        self.dry_run_outbox: list[dict[str, str | None]] = []

    async def send_sms(self, to: str, body: str, *, context_id: Optional[str] = None) -> bool:
        settings = get_settings()
        if settings.dry_run:
            self.dry_run_outbox.append({"to": to, "body": body, "context_id": context_id})
            log_event(logger, "SMS dry run", to=to, context_id=context_id, body_preview=body[:140])
            return True
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.api_base}/Messages.json",
                auth=(self.account_sid, self.auth_token),
                data={"To": to, "From": self.from_number, "Body": body},
            )
            response.raise_for_status()
        return True

    async def health_check(self) -> dict:
        if get_settings().dry_run:
            return {"ok": True, "mode": "dry_run"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_base}.json", auth=(self.account_sid, self.auth_token))
                response.raise_for_status()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


twilio_sms_client = TwilioSmsClient()
