"""Suppression tests."""
import pytest

from services.suppression import is_suppressed, suppress


@pytest.mark.asyncio
async def test_suppression_no_supabase_config_is_safe():
    assert await is_suppressed("+15551234567") is False
    await suppress("+15551234567", "STOP")
