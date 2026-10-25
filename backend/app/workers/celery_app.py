from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "teampulse",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="teampulse.ping")
def ping() -> str:
    return "pong"
