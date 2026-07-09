"""Campaign-level deduplication."""
from datetime import datetime, timedelta, timezone

from config import get_settings
from integrations.supabase_client import supabase_client
from models.campaign import CampaignType


async def already_contacted_this_cycle(phone: str, campaign_type: CampaignType) -> bool:
    since = datetime.now(timezone.utc) - timedelta(days=get_settings().contact_cycle_days)
    return await supabase_client.has_campaign_log(phone, campaign_type.value, since)
