from functools import lru_cache
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: int = Field(default=60, ge=1, le=180)
    openai_max_completion_tokens: int = Field(default=2048, ge=128, le=8192)
    database_url: str
    session_minutes: int = Field(default=60, ge=1, le=1440)
    cors_origins: list[str] = ["http://localhost:5173"]
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    return Settings()
