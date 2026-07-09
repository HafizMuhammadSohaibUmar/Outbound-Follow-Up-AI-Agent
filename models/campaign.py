"""Campaign domain models."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CampaignType(str, Enum):
    ESTIMATE_FOLLOWUP = "estimate_followup"
    JOB_REENGAGEMENT = "job_reengagement"
    SEASONAL = "seasonal"
    NOSHOW_RECOVERY = "noshow_recovery"


class ContactStatus(str, Enum):
    PENDING = "pending"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    DECLINED = "declined"
    SUPPRESSED = "suppressed"
    PAUSED = "paused"
    FAILED = "failed"


class ActionType(str, Enum):
    SMS = "sms"
    VOICE = "voice"
    SKIP = "skip"


class CampaignContact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    phone: str
    name: str
    business_id: str
    campaign_type: CampaignType
    status: ContactStatus = ContactStatus.PENDING
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
    outcome: Optional[str] = None
    custom_data: dict[str, Any] = Field(default_factory=dict)


class CampaignLog(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    business_id: str
    campaign_type: CampaignType
    contact_phone: str
    action_type: ActionType
    message_sent: str = ""
    outcome: str
    call_sid: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CampaignResult(BaseModel):
    campaign_type: CampaignType
    processed: int = 0
    sent: int = 0
    skipped: int = 0
    suppressed: int = 0
    errors: list[str] = Field(default_factory=list)
