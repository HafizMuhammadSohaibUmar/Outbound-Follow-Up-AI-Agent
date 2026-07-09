"""SMS message generation with deterministic fallback templates."""
from models.campaign import CampaignContact, CampaignType
from services.llm import complete_text


def fallback_message(contact: CampaignContact, business_name: str, owner_first_name: str) -> str:
    data = contact.custom_data
    if contact.campaign_type == CampaignType.ESTIMATE_FOLLOWUP:
        return (
            f"Hi {contact.name}, this is {owner_first_name} with {business_name}. "
            f"Just checking in on the {data.get('service_type', 'service')} estimate we sent. "
            "Would you like us to help get it scheduled?"
        )
    if contact.campaign_type == CampaignType.NOSHOW_RECOVERY:
        return (
            f"Hi {contact.name}, this is {owner_first_name} with {business_name}. "
            "Sorry we missed you for the appointment. Would you like us to find another time?"
        )
    return (
        f"Hi {contact.name}, this is {owner_first_name} with {business_name}. "
        f"We helped with your {data.get('service_type', 'home service')} before and wanted to see "
        "if you need anything scheduled this season."
    )


async def generate_campaign_message(contact: CampaignContact, business_name: str,
                                    owner_first_name: str, business_type: str) -> str:
    prompt = (
        "Write one concise SMS for a home-service customer. Use a warm, specific tone. "
        "No emojis. No markdown. Include the business name. Keep under 320 characters.\n"
        f"Business: {business_name}\nOwner: {owner_first_name}\nType: {business_type}\n"
        f"Campaign: {contact.campaign_type.value}\nCustomer: {contact.name}\n"
        f"Context: {contact.custom_data}"
    )
    try:
        text = await complete_text(
            [
                {"role": "system", "content": "You write compliant, practical SMS follow-ups."},
                {"role": "user", "content": prompt},
            ]
        )
        return text or fallback_message(contact, business_name, owner_first_name)
    except Exception:
        return fallback_message(contact, business_name, owner_first_name)
