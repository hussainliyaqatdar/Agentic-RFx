from functools import lru_cache

from google import genai

from app.config import get_settings


@lru_cache
def get_client() -> genai.Client:
    """Shared Gemini client, built once from the configured API key.

    Cached rather than a module-level global so tests can clear it
    (get_client.cache_clear()) and rebuild against a different key/settings.
    """
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


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
