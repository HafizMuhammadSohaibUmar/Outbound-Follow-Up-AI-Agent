"""Job completion re-engagement campaign."""
from config import get_settings
from integrations.housecallpro_reader import HousecallProReader
from integrations.jobber_reader import JobberReader
from models.campaign import CampaignContact, CampaignType
from utils import normalize_phone
from campaigns.estimate_followup import _first_phone, _name
from campaigns.base import CampaignRunner


class JobCompletionReEngagement(CampaignRunner):
    campaign_type = CampaignType.JOB_REENGAGEMENT

    async def load_contacts(self) -> list[CampaignContact]:
        rows = []
        for days in (30, 85, 150):
            for reader in (JobberReader(), HousecallProReader()):
                for row in await reader.get_completed_jobs(days_ago=days):
                    row["_days_ago"] = days
                    rows.append(row)
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
                            "job_id": row.get("id"),
                            "service_type": row.get("title") or row.get("service_type") or "service",
                            "completed_at": row.get("completedAt") or row.get("completed_at"),
                            "days_ago": row.get("_days_ago"),
                            "reason": self._reason(row),
                        },
                    )
                )
            except Exception:
                continue
        return contacts

    def _reason(self, row: dict) -> str:
        service = str(row.get("title") or row.get("service_type") or "").lower()
        days = row.get("_days_ago")
        if "pest" in service and days == 85:
            return "quarterly pest-control reminder"
        if any(word in service for word in ("hvac", "ac", "furnace", "heat")) and days == 150:
            return "pre-season HVAC reminder"
        if days == 30:
            return "30-day general re-engagement"
        return "service-specific re-engagement"
