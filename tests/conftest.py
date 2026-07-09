"""Test configuration."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.update({
    "BUSINESS_ID": "test-business",
    "BUSINESS_NAME": "Sohaib Systems",
    "BUSINESS_TYPE": "home services",
    "OWNER_FIRST_NAME": "Sohaib",
    "CLIENT_TIMEZONE": "America/New_York",
    "TWILIO_ACCOUNT_SID": "ACtest",
    "TWILIO_AUTH_TOKEN": "test",
    "TWILIO_PHONE_NUMBER": "+15550001111",
    "OWNER_PHONE_NUMBER": "+15550002222",
    "DRY_RUN": "true",
    "VALIDATE_TWILIO_SIGNATURE": "false",
    "CAMPAIGN_ADMIN_API_KEY": "test-admin-key",
    "SUPABASE_URL": "",
    "SUPABASE_KEY": "",
    "MISTRAL_API_KEY": "",
})
