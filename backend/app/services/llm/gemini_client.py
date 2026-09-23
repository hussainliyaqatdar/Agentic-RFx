from functools import lru_cache

import httpx
from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import get_settings

from . import cost_tracker


@lru_cache
def get_client() -> genai.Client:
    """Shared Gemini client, built once from the configured API key.

    Cached rather than a module-level global so tests can clear it
    (get_client.cache_clear()) and rebuild against a different key/settings.
    """
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


def _is_retryable(exc: BaseException) -> bool:
    # 503/UNAVAILABLE is genuine transient overload, worth a couple of retries.
    # 429/RESOURCE_EXHAUSTED on the free tier is a per-day quota, not a per-minute
    # rate limit - retrying it just burns more of the same exhausted daily budget.
    # Connection-level drops (proxy/network hiccups on a long request) are also
    # worth a retry - they're not the API telling us anything, just the wire.
    if isinstance(exc, (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadTimeout)):
        return True
    message = str(exc)
    return "UNAVAILABLE" in message or "503" in message


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    reraise=True,
)
def generate_content(*, model: str, contents, config: types.GenerateContentConfig, label: str = "call"):
    """generate_content with retry on transient server errors (503 high-demand),
    a hard session budget check before every call, and real cost logging (from the
    API's own token counts, not an estimate) after every call."""
    cost_tracker.check_budget_before_call()
    response = get_client().models.generate_content(model=model, contents=contents, config=config)
    cost_tracker.record_usage(response, label)
    return response


def ping() -> str:
    """Minimal live call used by the /health/llm endpoint to prove the API
    key in .env actually works, independent of any feature logic."""
    settings = get_settings()
    client = get_client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents="Reply with exactly one word: pong",
    )
    return (response.text or "").strip()
