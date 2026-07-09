"""Campaign runner tests."""
import pytest

from campaigns.estimate_followup import EstimateFollowUp
from campaigns.job_reengagement import JobCompletionReEngagement
from campaigns.noshow_recovery import NoShowRecovery
from campaigns.seasonal import SeasonalCampaign
from integrations.twilio_sms_client import twilio_sms_client
from models.campaign import CampaignContact, CampaignType


def contact(campaign_type: CampaignType) -> CampaignContact:
    return CampaignContact(
        phone="+15551234567",
        name="Jane Doe",
        business_id="test-business",
        campaign_type=campaign_type,
        custom_data={"service_type": "AC repair"},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("runner_cls,campaign_type", [
    (EstimateFollowUp, CampaignType.ESTIMATE_FOLLOWUP),
    (JobCompletionReEngagement, CampaignType.JOB_REENGAGEMENT),
    (NoShowRecovery, CampaignType.NOSHOW_RECOVERY),
])
async def test_sms_campaign_happy_path(runner_cls, campaign_type):
    twilio_sms_client.dry_run_outbox.clear()
    result = await runner_cls().run([contact(campaign_type)], force_run=True)

    assert result.sent == 1
    assert twilio_sms_client.dry_run_outbox
    assert "Sohaib Systems" in twilio_sms_client.dry_run_outbox[-1]["body"]


@pytest.mark.asyncio
async def test_seasonal_campaign_uses_voice_path():
    result = await SeasonalCampaign().run([contact(CampaignType.SEASONAL)], force_run=True)

    assert result.sent == 1


@pytest.mark.asyncio
async def test_suppression_path(monkeypatch):
    async def suppressed(_phone: str) -> bool:
        return True

    monkeypatch.setattr("campaigns.base.is_suppressed", suppressed)
    result = await EstimateFollowUp().run([contact(CampaignType.ESTIMATE_FOLLOWUP)], force_run=True)

    assert result.suppressed == 1
    assert result.sent == 0
