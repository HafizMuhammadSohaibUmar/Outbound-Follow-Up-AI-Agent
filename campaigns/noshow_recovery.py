"""No-show recovery campaign."""
from config import get_settings
from integrations.housecallpro_reader import HousecallProReader
from integrations.jobber_reader import JobberReader
from models.campaign import CampaignContact, CampaignType
from utils import normalize_phone
from campaigns.base import CampaignRunner
from campaigns.estimate_followup import _first_phone, _name


class NoShowRecovery(CampaignRunner):
    campaign_type = CampaignType.NOSHOW_RECOVERY

    async def load_contacts(self) -> list[CampaignContact]:
        rows = []
        for reader in (JobberReader(), HousecallProReader()):
            rows.extend(await reader.get_no_show_appointments(older_than_hours=2))
        contacts = []
        for row in rows:
            try:
                contacts.append(
                    CampaignContact(
                        phone=normalize_phone(_first_phone(row)),
                        name=_name(row),
                        business_id=get_settings().business_id,
                        campaign_type=self.campaign_type,
                        custom_data={
                            "appointment_id": row.get("id"),
                            "service_type": row.get("title") or row.get("service_type") or "appointment",
                            "recovery_schedule": "2 hours and 24 hours",
                        },
                    )
                )
            except Exception:
                continue
        return contacts

    def _attempt_allowed(self, contact: CampaignContact) -> bool:
        return contact.attempts < get_settings().noshow_max_attempts
