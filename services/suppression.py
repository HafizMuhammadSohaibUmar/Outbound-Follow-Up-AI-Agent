"""Suppression service."""
from integrations.supabase_client import supabase_client


async def is_suppressed(phone: str) -> bool:
    return await supabase_client.is_suppressed(phone)


async def suppress(phone: str, source: str = "manual") -> None:
    await supabase_client.suppress(phone, source)
