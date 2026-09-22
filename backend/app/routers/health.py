from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.services.llm import gemini_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict:
    return {"status": "ok"}


@router.get("/llm")
def health_llm() -> dict:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not set in .env")
    try:
        reply = gemini_client.ping()
    except Exception as exc:  # surface the provider's own error to the caller
        raise HTTPException(status_code=502, detail=f"Gemini call failed: {exc}") from exc
    return {"status": "ok", "model": settings.gemini_model, "reply": reply}
