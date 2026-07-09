"""Base campaign runner."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Iterable

from config import get_settings
from integrations.supabase_client import supabase_client
from integrations.twilio_sms_client import twilio_sms_client
from models.campaign import ActionType, CampaignContact, CampaignLog, CampaignResult, CampaignType, ContactStatus
from services.deduplication import already_contacted_this_cycle
from services.message_generator import generate_campaign_message
from services.suppression import is_suppressed
from utils import inside_calling_window


class CampaignRunner(ABC):
    campaign_type: CampaignType

    @abstractmethod
    async def load_contacts(self) -> list[CampaignContact]:
        """Load campaign candidates from FSM or manual input."""

    async def run(self, contacts: Iterable[CampaignContact] | None = None, *, force_run: bool = False) -> CampaignResult:
        settings = get_settings()
        result = CampaignResult(campaign_type=self.campaign_type)
        if await supabase_client.campaign_paused(self.campaign_type):
            return result
        if not force_run and not inside_calling_window(settings.client_timezone):
            return result
        candidates = list(contacts) if contacts is not None else await self.load_contacts()
        for contact in candidates:
            result.processed += 1
            try:
                contact.phone = contact.phone.strip()
                if await is_suppressed(contact.phone):
                    result.suppressed += 1
                    await self._log(contact, ActionType.SKIP, "", "suppressed")
                    continue
                existing = await supabase_client.get_contact(contact.phone, self.campaign_type)
                if existing:
                    contact.id = existing["id"]
                    contact.attempts = existing.get("attempts") or 0
                    contact.status = ContactStatus(existing.get("status") or ContactStatus.PENDING.value)
                if self._strict_cycle_dedup() and await already_contacted_this_cycle(contact.phone, self.campaign_type):
                    result.skipped += 1
                    await self._log(contact, ActionType.SKIP, "", "deduped")
                    continue
                if not self._attempt_allowed(contact):
                    result.skipped += 1
                    await self._log(contact, ActionType.SKIP, "", "max_attempts")
                    continue
                sent = await self._send(contact)
                contact.attempts += 1
                contact.status = ContactStatus.CONTACTED if sent else ContactStatus.FAILED
                contact.last_attempt_at = datetime.now(timezone.utc)
                await supabase_client.upsert_contact(contact)
                result.sent += 1 if sent else 0
            except Exception as exc:
                result.errors.append(str(exc))
        return result

    def _attempt_allowed(self, contact: CampaignContact) -> bool:
        return True

    def _strict_cycle_dedup(self) -> bool:
        return self.campaign_type in {CampaignType.JOB_REENGAGEMENT, CampaignType.SEASONAL}

    async def _send(self, contact: CampaignContact) -> bool:
        settings = get_settings()
        message = await generate_campaign_message(
            contact, settings.business_name, settings.owner_first_name, settings.business_type
        )
        sent = await twilio_sms_client.send_sms(contact.phone, message, context_id=str(contact.id))
        await self._log(contact, ActionType.SMS, message, "sent" if sent else "failed")
        return sent

    async def _log(self, contact: CampaignContact, action_type: ActionType,
                   message: str, outcome: str, call_sid: str | None = None) -> None:
        await supabase_client.log_campaign(
            CampaignLog(
                business_id=get_settings().business_id,
                campaign_type=self.campaign_type,
                contact_phone=contact.phone,
                action_type=action_type,
                message_sent=message,
                outcome=outcome,
                call_sid=call_sid,
            )
        )
