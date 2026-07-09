"""
Typed application settings, loaded from environment variables (and
optionally a .env file). Using pydantic-settings instead of scattered
module-level constants means:
  - misconfiguration fails fast at startup with a clear error
  - settings are mockable/injectable in tests instead of being globals
  - there's one documented place to see every knob the system exposes
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COGNOS_", env_file=".env", extra="ignore")

    # --- Capture ---
    poll_interval_seconds: float = Field(default=3.0, gt=0)
    excluded_apps: frozenset[str] = frozenset({"LockApp.exe"})

    # --- Reasoning / rate limiting ---
    min_seconds_between_llm_calls: float = Field(default=60.0, gt=0)
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = Field(default=100, gt=0)

    # --- Storage ---
    database_url: str = "sqlite:///./cognos.db"

    # --- API ---
    api_host: str = "127.0.0.1"
    api_port: int = 8420

    # --- Anthropic credentials ---
    anthropic_api_key: str | None = None

    @field_validator("excluded_apps", mode="before")
    @classmethod
    def _parse_excluded_apps(cls, v: object) -> object:
        if isinstance(v, str):
            return frozenset(x.strip() for x in v.split(",") if x.strip())
        return v


def get_settings() -> Settings:
    """Factory instead of a module-level singleton, so tests can override
    via environment variables per-test without import-order issues."""
    return Settings()