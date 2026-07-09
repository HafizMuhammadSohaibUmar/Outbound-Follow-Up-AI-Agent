"""LiteLLM wrapper for personalization."""
import asyncio
import os
from typing import Any

import litellm

from config import get_settings

litellm.suppress_debug_info = True


async def complete_text(messages: list[dict[str, str]], *, max_tokens: int = 180) -> str:
    settings = get_settings()
    if settings.mistral_api_key:
        os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key
    response: Any = await asyncio.wait_for(
        litellm.acompletion(
            model=settings.primary_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.35,
            timeout=settings.llm_timeout_seconds,
        ),
        timeout=settings.llm_timeout_seconds + 1,
    )
    return (response.choices[0].message.content or "").strip()
