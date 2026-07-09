"""Application configuration for the outbound follow-up agent."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    business_id: str = "default-business"
    business_name: str = "Acme Home Services"
    business_type: str = "home services"
    owner_first_name: str = "Sam"
    client_timezone: str = "America/New_York"

    host: str = "0.0.0.0"
    port: int = 8003
    public_base_url: str = "http://localhost:8003"
    log_level: str = "INFO"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    owner_phone_number: str = ""
    dry_run: bool = True
    demo_mode_enabled: bool = True
    demo_owner_phone_number: str = "+15550002222"
    campaign_admin_api_key: str = "change_me_campaign_admin_key"
    validate_twilio_signature: bool = True

    mistral_api_key: str = ""
    primary_model: str = "mistral/mistral-small-latest"
    llm_timeout_seconds: float = 6.0

    supabase_url: str = ""
    supabase_key: str = ""

    jobber_api_token: str = ""
    jobber_api_base_url: str = "https://api.getjobber.com/api/graphql"
    housecallpro_api_token: str = ""
    housecallpro_api_base_url: str = "https://api.housecallpro.com"

    agent1_repo_path: str = "../"
    agent1_public_base_url: str = "http://localhost:8000"
    outbound_voice_webhook_path: str = "/voice/outbound"

    estimate_followup_max_attempts: int = 2
    noshow_max_attempts: int = 2
    contact_cycle_days: int = 180

    seasonal_hvac_dates: str = "04-01,09-15"
    seasonal_pest_dates: str = "03-01,06-01,09-01"
    seasonal_roofing_dates: str = "03-15"


@lru_cache
def get_settings() -> Settings:
    return Settings()
