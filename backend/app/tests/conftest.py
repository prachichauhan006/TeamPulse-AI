import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-for-teampulse-with-32-plus-characters"
os.environ["AI_PROVIDER"] = "mock"

import httpx
import pytest
import pytest_asyncio

from app import models  # noqa: F401
from app.db.base import Base
from app.db.session import engine
from app.main import app
from app.services.rate_limit import ai_user_rate_limiter, login_rate_limiter, search_user_rate_limiter


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    for limiter in (login_rate_limiter, ai_user_rate_limiter, search_user_rate_limiter):
        limiter.reset_for_tests()
    yield
    for limiter in (login_rate_limiter, ai_user_rate_limiter, search_user_rate_limiter):
        limiter.reset_for_tests()


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
