"""Service configuration, read from environment variables or a local .env file."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

VERSION = "0.1.0"
"""Version of the service. It changes with each release."""

MODEL_VERSION = "rules-v1"
"""Version of the models. Every response includes it as modelVersion."""


class Settings(BaseSettings):
    """Environment variables of the service, all with the AI_SERVICE_ prefix."""

    model_config = SettingsConfigDict(env_prefix="AI_SERVICE_", env_file=".env", extra="ignore")

    api_key: str = Field(min_length=16)
    """Shared secret that auxia-backend sends in the X-API-Key header."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
