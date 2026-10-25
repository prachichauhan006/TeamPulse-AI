import logging
import time
import uuid
from typing import TypeAlias

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.embedding import Embedding
from app.models.enums import EmbeddingSourceType, EmbeddingStatus
from app.models.meeting_note import MeetingNote
from app.services.ai.base import TransientAIProviderError
from app.services.ai.factory import get_ai_provider
from app.services.ai.schemas import EmbeddingVector

logger = logging.getLogger(__name__)
SourceModel: TypeAlias = Document | MeetingNote
EMBEDDING_FAILURE_MESSAGE = "Embedding generation failed. Text search remains available."


def chunk_text(text: str, chunk_words: int = 800, overlap_words: int = 80) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    step = chunk_words - overlap_words
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_words]).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_words >= len(words):
            break
    return chunks


def _get_source(
    db: Session,
    source_type: EmbeddingSourceType,
    source_id: uuid.UUID,
    workspace_id: uuid.UUID,
    include_deleted: bool = False,
) -> SourceModel | None:
    model = Document if source_type == EmbeddingSourceType.DOCUMENT else MeetingNote
    filters = [model.id == source_id, model.workspace_id == workspace_id]
    if not include_deleted:
        filters.append(model.deleted_at.is_(None))
    return db.scalar(select(model).where(*filters))


def _generate_vectors(chunks: list[str]) -> list[list[float]]:
    provider = get_ai_provider()
    vectors: list[list[float]] = []
    for chunk in chunks:
        for attempt in range(3):
            try:
                vectors.append(EmbeddingVector(values=provider.generate_embedding(chunk)).values)
                break
            except TransientAIProviderError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
    return vectors


def _mark_failed(
    source_type: EmbeddingSourceType,
    source_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    try:
        with SessionLocal() as db:
            source = _get_source(db, source_type, source_id, workspace_id, include_deleted=True)
            if source is not None:
                source.embedding_status = EmbeddingStatus.FAILED
                source.embedding_error = EMBEDDING_FAILURE_MESSAGE
                db.commit()
    except Exception as exc:
        logger.error("Unable to record embedding failure with %s", type(exc).__name__)


def generate_source_embeddings(
    source_type: EmbeddingSourceType,
    source_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> dict[str, int | str]:
    """Generate and atomically replace a source's chunks; safe to run repeatedly."""
    with SessionLocal() as db:
        source = _get_source(db, source_type, source_id, workspace_id)
        if source is None:
            return {"status": "skipped", "chunks": 0}
        source.embedding_status = EmbeddingStatus.PROCESSING
        source.embedding_error = None
        content = source.content
        db.commit()

    try:
        chunks = chunk_text(content)
        vectors = _generate_vectors(chunks)
        with SessionLocal() as db:
            source = _get_source(db, source_type, source_id, workspace_id)
            if source is None:
                return {"status": "skipped", "chunks": 0}
            db.execute(
                delete(Embedding).where(
                    Embedding.workspace_id == workspace_id,
                    Embedding.source_type == source_type,
                    Embedding.source_id == source_id,
                )
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                db.add(
                    Embedding(
                        workspace_id=workspace_id,
                        source_type=source_type,
                        source_id=source_id,
                        chunk_index=index,
                        content_snippet=chunk[:2_000],
                        embedding=vector,
                    )
                )
            source.embedding_status = EmbeddingStatus.COMPLETE
            source.embedding_error = None
            db.commit()
        return {"status": "complete", "chunks": len(chunks)}
    except Exception as exc:
        # Do not log provider bodies, source content, request headers, or keys.
        logger.error("Embedding job failed with %s", type(exc).__name__)
        _mark_failed(source_type, source_id, workspace_id)
        return {"status": "failed", "chunks": 0}


def schedule_source_embedding(
    source_type: EmbeddingSourceType,
    source_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    """Run inline only in tests; otherwise enqueue without failing source creation."""
    if get_settings().app_env == "test":
        generate_source_embeddings(source_type, source_id, workspace_id)
        return
    try:
        from app.workers.tasks import generate_embedding_task

        generate_embedding_task.delay(source_type.value, str(source_id), str(workspace_id))
    except Exception as exc:
        logger.error("Embedding enqueue failed with %s", type(exc).__name__)
        _mark_failed(source_type, source_id, workspace_id)
