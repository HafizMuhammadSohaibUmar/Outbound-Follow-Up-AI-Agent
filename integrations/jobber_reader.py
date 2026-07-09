"""Read-only Jobber FSM reader."""
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from config import get_settings


class JobberReader:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_token = settings.jobber_api_token
        self.api_base = settings.jobber_api_base_url

    async def _graphql(self, query: str, variables: dict[str, Any]) -> dict:
        if not self.api_token:
            return {}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                self.api_base,
                headers={"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"},
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()
        return response.json()

    async def get_pending_estimates(self, older_than_hours: int) -> list[dict]:
        threshold = (datetime.now(timezone.utc) - timedelta(hours=older_than_hours)).isoformat()
        query = "query($threshold: ISO8601DateTime!){ quotes(filter:{status:PENDING,createdBefore:$threshold}){nodes{id client{name phones{number}} title total createdAt}}}"
        data = await self._graphql(query, {"threshold": threshold})
        return _jobber_nodes(data, "quotes")

    async def get_completed_jobs(self, days_ago: int) -> list[dict]:
        target = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()
        query = "query($date: ISO8601Date!){ jobs(filter:{completedOn:$date}){nodes{id client{name phones{number}} title completedAt}}}"
        data = await self._graphql(query, {"date": target})
        return _jobber_nodes(data, "jobs")

    async def get_all_customers(self, since_months: int) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=since_months * 30)).date().isoformat()
        query = "query($since: ISO8601Date!){ clients(filter:{updatedAfter:$since}){nodes{id name phones{number}}}}"
        data = await self._graphql(query, {"since": since})
        return _jobber_nodes(data, "clients")

    async def get_no_show_appointments(self, older_than_hours: int) -> list[dict]:
        before = (datetime.now(timezone.utc) - timedelta(hours=older_than_hours)).isoformat()
        query = "query($before: ISO8601DateTime!){ visits(filter:{status:MISSED,startsBefore:$before}){nodes{id title startAt client{name phones{number}}}}}"
        data = await self._graphql(query, {"before": before})
        return _jobber_nodes(data, "visits")


def _jobber_nodes(data: dict, key: str) -> list[dict]:
    return (((data.get("data") or {}).get(key) or {}).get("nodes") or [])
