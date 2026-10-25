from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "TeamPulse AI"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str
    redis_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:5173"
    trust_proxy_headers: bool = False
    ai_provider: Literal["mock", "openai_compatible"] = "mock"
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    document_max_upload_mb: int = Field(default=5, ge=1, le=5)

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
        if value.lower().startswith(("replace-", "change-me", "changeme")):
            raise ValueError("JWT_SECRET_KEY must be replaced with a random value")
        return value

    @model_validator(mode="after")
    def validate_production_cors(self) -> "Settings":
        if self.app_env == "production" and "*" in self.cors_origin_list:
            raise ValueError("Wildcard CORS is not allowed in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
