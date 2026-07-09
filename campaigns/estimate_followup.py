"""Estimate follow-up campaign."""
from config import get_settings
from integrations.housecallpro_reader import HousecallProReader
from integrations.jobber_reader import JobberReader
from models.campaign import CampaignContact, CampaignType
from utils import normalize_phone
from campaigns.base import CampaignRunner


class EstimateFollowUp(CampaignRunner):
    campaign_type = CampaignType.ESTIMATE_FOLLOWUP

    async def load_contacts(self) -> list[CampaignContact]:
        rows = []
        for reader in (JobberReader(), HousecallProReader()):
            rows.extend(await reader.get_pending_estimates(older_than_hours=48))
        return [self._to_contact(row) for row in rows if self._has_phone(row)]

    def _attempt_allowed(self, contact: CampaignContact) -> bool:
        return contact.attempts < get_settings().estimate_followup_max_attempts

    def _to_contact(self, row: dict) -> CampaignContact:
        phone = _first_phone(row)
        return CampaignContact(
            phone=normalize_phone(phone),
            name=_name(row),
            business_id=get_settings().business_id,
            campaign_type=self.campaign_type,
            custom_data={
                "estimate_id": row.get("id"),
                "service_type": row.get("title") or row.get("service_type") or "service",
                "amount": row.get("total") or row.get("amount"),
                "followup_schedule": "day 2 and day 5",
            },
        )

    def _has_phone(self, row: dict) -> bool:
        try:
            normalize_phone(_first_phone(row))
            return True
        except Exception:
            return False


def _first_phone(row: dict) -> str:
    phones = row.get("phones") or row.get("client", {}).get("phones") or row.get("customer", {}).get("phones") or []
    if isinstance(phones, list) and phones:
        first = phones[0]
        return first.get("number") if isinstance(first, dict) else str(first)
    return row.get("phone") or row.get("phone_number") or ""


def _name(row: dict) -> str:
    client = row.get("client") or row.get("customer") or {}
    return row.get("name") or client.get("name") or "there"
