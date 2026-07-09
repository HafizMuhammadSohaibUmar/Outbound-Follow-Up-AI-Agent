"""Seasonal outbound voice campaign."""
from datetime import datetime

from campaigns.base import CampaignRunner
from config import get_settings
from integrations.housecallpro_reader import HousecallProReader
from integrations.jobber_reader import JobberReader
from integrations.outbound_call_service import outbound_call_service
from models.campaign import ActionType, CampaignContact, CampaignType
from utils import normalize_phone


class SeasonalCampaign(CampaignRunner):
    campaign_type = CampaignType.SEASONAL

    async def load_contacts(self) -> list[CampaignContact]:
        if not _is_launch_day():
            return []
        rows = []
        for reader in (JobberReader(), HousecallProReader()):
            rows.extend(await reader.get_all_customers(since_months=24))
        contacts = []
        for row in rows:
            try:
                contacts.append(
                    CampaignContact(
                        phone=normalize_phone(_phone(row)),
                        name=row.get("name") or row.get("customer_name") or "there",
                        business_id=get_settings().business_id,
                        campaign_type=self.campaign_type,
                        custom_data={"customer_id": row.get("id"), "service_type": _seasonal_service()},
                    )
                )
            except Exception:
                continue
        return contacts

    async def _send(self, contact: CampaignContact) -> bool:
        response = await outbound_call_service.start_call(
            contact.phone,
            campaign_type=self.campaign_type.value,
            context={"name": contact.name, **contact.custom_data},
        )
        await self._log(
            contact,
            ActionType.VOICE,
            f"Seasonal voice call for {contact.custom_data.get('service_type', 'service')}",
            "voice_started" if response.get("ok") else "failed",
            call_sid=response.get("call_sid"),
        )
        return bool(response.get("ok"))


def _phone(row: dict) -> str:
    phones = row.get("phones") or []
    if phones:
        first = phones[0]
        return first.get("number") if isinstance(first, dict) else str(first)
    return row.get("phone") or row.get("phone_number") or ""


def _seasonal_service() -> str:
    today = datetime.now().strftime("%m-%d")
    settings = get_settings()
    if today in settings.seasonal_hvac_dates.split(","):
        return "HVAC tune-up"
    if today in settings.seasonal_pest_dates.split(","):
        return "pest control service"
    if today in settings.seasonal_roofing_dates.split(","):
        return "roof inspection"
    return "seasonal home service"


def _is_launch_day() -> bool:
    today = datetime.now().strftime("%m-%d")
    settings = get_settings()
    configured = (
        settings.seasonal_hvac_dates.split(",")
        + settings.seasonal_pest_dates.split(",")
        + settings.seasonal_roofing_dates.split(",")
    )
    return today in {day.strip() for day in configured}
