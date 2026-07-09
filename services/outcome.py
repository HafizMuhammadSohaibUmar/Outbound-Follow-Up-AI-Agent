"""Classify customer replies and update campaign outcomes."""
from datetime import datetime, timezone

from config import get_settings
from integrations.supabase_client import supabase_client
from integrations.twilio_sms_client import twilio_sms_client
from models.campaign import ActionType, CampaignLog, CampaignType, ContactStatus
from services.suppression import suppress

STOP_WORDS = {"STOP", "UNSUBSCRIBE", "CANCEL", "QUIT", "END", "OPTOUT", "OPT OUT"}
ACCEPT_WORDS = {"YES", "BOOK", "SCHEDULE", "ACCEPT", "APPROVE", "INTERESTED", "CALL ME"}
DECLINE_WORDS = {"NO", "DECLINE", "NOT INTERESTED", "TOO EXPENSIVE", "CANCEL"}


def classify_reply(body: str) -> str:
    text = " ".join((body or "").upper().split())
    if text in STOP_WORDS:
        return "stop"
    if any(word in text for word in ACCEPT_WORDS):
        return "accepted"
    if any(word in text for word in DECLINE_WORDS):
        return "declined"
    return "needs_followup"


async def handle_customer_reply(phone: str, body: str, message_sid: str = "") -> dict:
    contact = await supabase_client.latest_contact_for_phone(phone)
    outcome = classify_reply(body)
    if outcome == "stop":
        await suppress(phone, "STOP")
        await twilio_sms_client.send_sms(phone, "You are opted out and will not receive more follow-up messages.")
        return {"status": "suppressed", "outcome": outcome}
    if not contact:
        return {"status": "ignored", "outcome": "no_campaign_contact"}
    campaign_type = contact["campaign_type"]
    if outcome == "accepted":
        await supabase_client.update_contact_by_phone(
            phone, campaign_type, status=ContactStatus.CONVERTED.value, outcome=outcome
        )
        await twilio_sms_client.send_sms(
            get_settings().owner_phone_number,
            f"Follow-up lead ready: {contact.get('name')} ({phone}) replied: {body}",
            context_id=message_sid,
        )
    elif outcome == "declined":
        await supabase_client.update_contact_by_phone(
            phone, campaign_type, status=ContactStatus.DECLINED.value, outcome=outcome
        )
    else:
        await supabase_client.update_contact_by_phone(phone, campaign_type, outcome=outcome)
    await supabase_client.log_campaign(
        CampaignLog(
            business_id=get_settings().business_id,
            campaign_type=CampaignType(campaign_type),
            contact_phone=phone,
            action_type=ActionType.SMS,
            message_sent=body,
            outcome="converted" if outcome == "accepted" else outcome,
            created_at=datetime.now(timezone.utc),
        )
    )
    return {"status": "ok", "campaign_type": campaign_type, "outcome": outcome}
