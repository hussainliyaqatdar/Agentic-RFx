from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    database_url: str = "sqlite:///./agentic_rfx.db"
    storage_dir: str = "./storage"
    seed_data_dir: str = str(_REPO_ROOT / "data" / "seed")


@lru_cache
def get_settings() -> Settings:
    return Settings()
