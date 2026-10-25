import uuid

from app.models.enums import EmbeddingSourceType
from app.services.embeddings import generate_source_embeddings
from app.workers.celery_app import celery_app


@celery_app.task(name="teampulse.embeddings.generate")
def generate_embedding_task(source_type: str, source_id: str, workspace_id: str) -> dict[str, int | str]:
    return generate_source_embeddings(
        EmbeddingSourceType(source_type), uuid.UUID(source_id), uuid.UUID(workspace_id)
    )
