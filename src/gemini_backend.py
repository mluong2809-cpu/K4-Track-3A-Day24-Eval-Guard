"""Shared Gemini chat client using Google's OpenAI-compatible endpoint."""

from functools import lru_cache
import asyncio
import threading
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from config import GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL

_rate_lock = threading.Lock()
_next_request_at = 0.0


def _reserve_slot() -> float:
    """Reserve a Gemini request start below the 15/minute free-tier limit."""
    global _next_request_at
    with _rate_lock:
        now = time.monotonic()
        start = max(now, _next_request_at)
        _next_request_at = start + 4.5
    return max(0.0, start - now)


def wait_for_slot() -> None:
    time.sleep(_reserve_slot())


class RateLimitedGeminiChat(BaseChatModel):
    """LangChain chat adapter for NeMo with honest API quota pacing."""

    delegate: Any

    @property
    def _llm_type(self) -> str:
        return "rate_limited_gemini_chat"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        wait_for_slot()
        return self.delegate._generate(messages, stop=stop, run_manager=run_manager,
                                       **kwargs)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        from openai import APIStatusError

        for attempt in range(5):
            await asyncio.sleep(_reserve_slot())
            try:
                return await self.delegate._agenerate(messages, stop=stop,
                                                      run_manager=run_manager, **kwargs)
            except APIStatusError as error:
                if error.status_code not in (429, 503) or attempt == 4:
                    raise
                await asyncio.sleep(65 if error.status_code == 429 else min(10 * 2**attempt, 60))


@lru_cache(maxsize=1)
def _client():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is unavailable")
    from openai import OpenAI

    return OpenAI(
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_BASE_URL,
        timeout=30.0,
        max_retries=1,
    )


def chat(system: str, user: str, *, json_mode: bool = False, max_tokens: int = 1024) -> str:
    options = {"response_format": {"type": "json_object"}} if json_mode else {}
    response = _client().chat.completions.create(
        model=GEMINI_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        reasoning_effort="low",
        max_tokens=max_tokens,
        **options,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("Gemini returned an empty answer")
    return content
