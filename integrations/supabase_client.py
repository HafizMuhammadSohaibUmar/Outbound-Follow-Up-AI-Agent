"""Async Supabase PostgREST client."""
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from config import get_settings
from models.campaign import CampaignContact, CampaignLog, CampaignType, ContactStatus


def _mask_phone(phone: str | None) -> str:
    if not phone:
        return ""
    return f"{phone[:3]}***{phone[-4:]}" if len(phone) >= 7 else "***"


class SupabaseClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.supabase_url.rstrip("/")
        self.business_id = settings.business_id
        self.headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _url(self, table: str) -> str:
        return f"{self.base_url}/rest/v1/{table}"

    async def _request(self, method: str, table: str, *,
                       params: Optional[dict] = None, json: Any = None) -> list[dict]:
        if not self.base_url or not get_settings().supabase_key:
            return []
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                method, self._url(table), headers=self.headers, params=params, json=json
            )
            response.raise_for_status()
        return response.json() if response.content else []

    async def is_suppressed(self, phone: str) -> bool:
        rows = await self._request(
            "GET", "suppression_list",
            params={
                "business_id": f"eq.{self.business_id}",
                "phone_number": f"eq.{phone}",
                "select": "phone_number",
                "limit": "1",
            },
        )
        return bool(rows)

    async def suppress(self, phone: str, source: str) -> None:
        if await self.is_suppressed(phone):
            return
        await self._request(
            "POST", "suppression_list",
            json={"business_id": self.business_id, "phone_number": phone, "reason": source, "source": source},
        )

    async def upsert_contact(self, contact: CampaignContact) -> dict:
        rows = await self._request(
            "POST",
            "campaign_contacts",
            json=contact.model_dump(mode="json"),
            params={"on_conflict": "business_id,phone,campaign_type"},
        )
        return rows[0] if rows else contact.model_dump(mode="json")

    async def get_contact(self, phone: str, campaign_type: CampaignType) -> dict | None:
        rows = await self._request(
            "GET", "campaign_contacts",
            params={
                "business_id": f"eq.{self.business_id}",
                "phone": f"eq.{phone}",
                "campaign_type": f"eq.{campaign_type.value}",
                "select": "*",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    async def latest_contact_for_phone(self, phone: str) -> dict | None:
        rows = await self._request(
            "GET", "campaign_contacts",
            params={
                "business_id": f"eq.{self.business_id}",
                "phone": f"eq.{phone}",
                "select": "*",
                "order": "last_attempt_at.desc.nullslast,created_at.desc",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    async def update_contact_by_phone(self, phone: str, campaign_type: str, **fields: Any) -> None:
        await self._request(
            "PATCH", "campaign_contacts",
            params={
                "business_id": f"eq.{self.business_id}",
                "phone": f"eq.{phone}",
                "campaign_type": f"eq.{campaign_type}",
            },
            json=fields,
        )

    async def update_contact(self, contact_id: str, **fields: Any) -> None:
        await self._request(
            "PATCH", "campaign_contacts",
            params={"id": f"eq.{contact_id}", "business_id": f"eq.{self.business_id}"},
            json=fields,
        )

    async def log_campaign(self, log: CampaignLog) -> None:
        await self._request("POST", "campaign_logs", json=log.model_dump(mode="json"))

    async def log_voice_status(self, phone: str, call_sid: str, outcome: str) -> None:
        contact = await self.latest_contact_for_phone(phone)
        campaign_type = contact["campaign_type"] if contact else CampaignType.SEASONAL.value
        await self.log_campaign(
            CampaignLog(
                business_id=self.business_id,
                campaign_type=CampaignType(campaign_type),
                contact_phone=phone,
                action_type="voice",
                message_sent="",
                outcome=outcome,
                call_sid=call_sid,
            )
        )

    async def has_campaign_log(self, phone: str, campaign_type: str, since: datetime) -> bool:
        rows = await self._request(
            "GET", "campaign_logs",
            params={
                "business_id": f"eq.{self.business_id}",
                "contact_phone": f"eq.{phone}",
                "campaign_type": f"eq.{campaign_type}",
                "created_at": f"gte.{since.isoformat()}",
                "select": "id",
                "limit": "1",
            },
        )
        return bool(rows)

    async def campaign_paused(self, campaign_type: CampaignType) -> bool:
        rows = await self._request(
            "GET", "campaign_state",
            params={
                "business_id": f"eq.{self.business_id}",
                "campaign_type": f"eq.{campaign_type.value}",
                "select": "paused",
                "limit": "1",
            },
        )
        return bool(rows and rows[0].get("paused"))

    async def set_campaign_paused(self, campaign_type: CampaignType, paused: bool) -> None:
        await self._request(
            "POST", "campaign_state",
            params={"on_conflict": "business_id,campaign_type"},
            json={"business_id": self.business_id, "campaign_type": campaign_type.value, "paused": paused},
        )

    async def metrics(self) -> dict:
        rows = await self._request(
            "GET", "campaign_logs",
            params={
                "business_id": f"eq.{self.business_id}",
                "select": "campaign_type,outcome,created_at",
                "order": "created_at.desc",
                "limit": "1000",
            },
        )
        grouped: dict[str, dict[str, float]] = {}
        for row in rows:
            bucket = grouped.setdefault(row["campaign_type"], {"contacts": 0, "converted": 0})
            if row.get("outcome") in {"sent", "voice_started", "converted"}:
                bucket["contacts"] += 1
            if row.get("outcome") == "converted":
                bucket["converted"] += 1
        for bucket in grouped.values():
            contacts = bucket["contacts"] or 1
            bucket["conversion_rate"] = round(bucket["converted"] / contacts, 4)
        return grouped

    async def demo_snapshot(self) -> dict:
        contacts = await self._request(
            "GET", "campaign_contacts",
            params={
                "business_id": f"eq.{self.business_id}",
                "select": "phone,campaign_type,status,attempts,outcome,last_attempt_at",
                "order": "last_attempt_at.desc.nullslast",
                "limit": "6",
            },
        )
        logs = await self._request(
            "GET", "campaign_logs",
            params={
                "business_id": f"eq.{self.business_id}",
                "select": "campaign_type,contact_phone,action_type,outcome,created_at",
                "order": "created_at.desc",
                "limit": "6",
            },
        )
        return {
            "tables": {
                "campaign_contacts": {
                    "sample": [
                        {
                            "phone": _mask_phone(row.get("phone")),
                            "campaign_type": row.get("campaign_type"),
                            "status": row.get("status"),
                            "attempts": row.get("attempts"),
                            "outcome": row.get("outcome"),
                            "last_attempt_at": row.get("last_attempt_at"),
                        }
                        for row in contacts
                    ],
                },
                "campaign_logs": {
                    "sample": [
                        {
                            "phone": _mask_phone(row.get("contact_phone")),
                            "campaign_type": row.get("campaign_type"),
                            "action_type": row.get("action_type"),
                            "outcome": row.get("outcome"),
                            "created_at": row.get("created_at"),
                        }
                        for row in logs
                    ],
                },
            }
        }

    async def health_check(self) -> dict:
        try:
            await self._request("GET", "campaign_logs", params={"select": "id", "limit": "1"})
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


supabase_client = SupabaseClient()
