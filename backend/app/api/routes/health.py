import redis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import get_settings

router = APIRouter(tags=["operations"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(db: DbSession) -> JSONResponse:
    components = {"database": "unavailable", "redis": "unavailable"}
    try:
        db.execute(text("SELECT 1"))
        components["database"] = "ok"
    except Exception:
        db.rollback()

    client = redis.Redis.from_url(
        get_settings().redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        if client.ping():
            components["redis"] = "ok"
    except redis.RedisError:
        pass
    finally:
        client.close()

    is_ready = all(value == "ok" for value in components.values())
    return JSONResponse(
        status_code=status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if is_ready else "not_ready", "components": components},
    )
