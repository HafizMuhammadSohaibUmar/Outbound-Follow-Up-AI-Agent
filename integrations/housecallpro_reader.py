"""Read-only Housecall Pro FSM reader."""
from datetime import datetime, timedelta, timezone

import httpx

from config import get_settings


class HousecallProReader:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_token = settings.housecallpro_api_token
        self.api_base = settings.housecallpro_api_base_url.rstrip("/")

    async def _get(self, path: str, params: dict) -> list[dict]:
        if not self.api_token:
            return []
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.api_base}{path}",
                headers={"Authorization": f"Token {self.api_token}"},
                params=params,
            )
            response.raise_for_status()
        payload = response.json()
        return payload.get("data") or payload.get("jobs") or payload.get("estimates") or payload.get("customers") or []

    async def get_pending_estimates(self, older_than_hours: int) -> list[dict]:
        before = (datetime.now(timezone.utc) - timedelta(hours=older_than_hours)).isoformat()
        return await self._get("/estimates", {"status": "pending", "created_before": before})

    async def get_completed_jobs(self, days_ago: int) -> list[dict]:
        date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()
        return await self._get("/jobs", {"status": "completed", "completed_on": date})

    async def get_all_customers(self, since_months: int) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=since_months * 30)).date().isoformat()
        return await self._get("/customers", {"updated_after": since})

    async def get_no_show_appointments(self, older_than_hours: int) -> list[dict]:
        before = (datetime.now(timezone.utc) - timedelta(hours=older_than_hours)).isoformat()
        return await self._get("/jobs", {"status": "missed", "scheduled_before": before})
