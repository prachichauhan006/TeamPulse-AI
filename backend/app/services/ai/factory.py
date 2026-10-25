from functools import lru_cache

from app.core.config import get_settings
from app.services.ai.base import AIProvider
from app.services.ai.mock import MockAIProvider
from app.services.ai.openai_compatible import OpenAICompatibleProvider


@lru_cache
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "openai_compatible":
        return OpenAICompatibleProvider(settings)
    return MockAIProvider()
