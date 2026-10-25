import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.services.ai.base import AIProviderError
from app.services.ai.openai_compatible import OpenAICompatibleProvider


def settings(provider: str, api_key: str | None = None) -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
        jwt_secret_key="test-only-secret-key-for-teampulse-with-32-plus-characters",
        ai_provider=provider,
        openai_api_key=SecretStr(api_key) if api_key else None,
    )


def test_openai_compatible_is_the_only_remote_provider_name():
    configured = settings("openai_compatible", "test-only-not-a-real-key")
    assert configured.ai_provider == "openai_compatible"
    with pytest.raises(ValidationError):
        settings("openai")


def test_remote_provider_without_a_key_fails_safely_before_any_request():
    with pytest.raises(AIProviderError, match="not configured"):
        OpenAICompatibleProvider(settings("openai_compatible"))
