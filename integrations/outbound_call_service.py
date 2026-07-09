"""Outbound voice adapter that reuses the Agent 1 voice pipeline boundary."""
import importlib.util
import logging
import sys
from pathlib import Path

import httpx

from config import get_settings
from logging_utils import log_event

logger = logging.getLogger("outbound_call")


class OutboundCallService:
    """Starts calls through Twilio and points them at the self-hosted voice webhook.

    The live conversation pipeline stays in Agent 1: Twilio Media Streams,
    Deepgram STT, LiteLLM, and ElevenLabs Flash TTS. This service imports the
    Agent 1 repo path when available so deployment failures are caught early,
    then creates an outbound call to the configured webhook.
    """

    def __init__(self) -> None:
        self.agent1_available = self._probe_agent1_repo()

    def _probe_agent1_repo(self) -> bool:
        root = Path(get_settings().agent1_repo_path).resolve()
        main_file = root / "main.py"
        if not main_file.exists():
            return False
        try:
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            return importlib.util.find_spec("integrations.deepgram_client") is not None
        except Exception:
            return False

    async def start_call(self, to: str, *, campaign_type: str, context: dict) -> dict:
        settings = get_settings()
        if settings.dry_run:
            return {
                "ok": True,
                "mode": "dry_run",
                "call_sid": f"dry-run-{campaign_type}-{to[-4:]}",
                "agent1_available": self.agent1_available,
            }
        twiml_url = settings.agent1_public_base_url.rstrip("/") + "/voice"
        api_base = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{api_base}/Calls.json",
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                data={
                    "To": to,
                    "From": settings.twilio_phone_number,
                    "Url": twiml_url,
                    "StatusCallback": settings.public_base_url.rstrip("/") + "/voice/outbound/status",
                    "StatusCallbackEvent": "initiated ringing answered completed",
                },
            )
            response.raise_for_status()
        payload = response.json()
        log_event(logger, "Outbound call started", to=to, campaign_type=campaign_type)
        return {"ok": True, "call_sid": payload.get("sid"), "agent1_available": self.agent1_available}


outbound_call_service = OutboundCallService()
