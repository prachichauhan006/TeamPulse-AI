import logging
import math
import re
import uuid
from difflib import SequenceMatcher
from typing import Literal

from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.embedding import Embedding
from app.models.enums import EmbeddingSourceType
from app.models.meeting_note import MeetingNote
from app.models.task import Task
from app.schemas.search import DuplicateTaskSuggestion, SearchResult
from app.services.ai.base import AIProviderError
from app.services.ai.factory import get_ai_provider
from app.services.ai.schemas import EmbeddingVector

logger = logging.getLogger(__name__)
SearchType = Literal["document", "meeting_note", "task"]


def cosine_similarity(first: list[float], second: list[float]) -> float:
    dot = sum(a * b for a, b in zip(first, second, strict=True))
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if not first_norm or not second_norm:
        return 0.0
    return dot / (first_norm * second_norm)


def _snippet(content: str, query: str, length: int = 350) -> str:
    cleaned = " ".join(content.split())
    index = cleaned.lower().find(query.lower())
    if index < 0:
        return cleaned[:length]
    start = max(0, index - 80)
    excerpt = cleaned[start : start + length]
    return f"{'…' if start else ''}{excerpt}{'…' if start + length < len(cleaned) else ''}"


def _active_source_titles(
    db: Session,
    workspace_id: uuid.UUID,
    search_type: SearchType | None,
) -> dict[EmbeddingSourceType, dict[uuid.UUID, str]]:
    result: dict[EmbeddingSourceType, dict[uuid.UUID, str]] = {
        EmbeddingSourceType.DOCUMENT: {},
        EmbeddingSourceType.MEETING_NOTE: {},
    }
    if search_type in (None, "document"):
        result[EmbeddingSourceType.DOCUMENT] = {
            row.id: row.title
            for row in db.execute(
                select(Document.id, Document.title).where(
                    Document.workspace_id == workspace_id,
                    Document.deleted_at.is_(None),
                )
            ).all()
        }
    if search_type in (None, "meeting_note"):
        result[EmbeddingSourceType.MEETING_NOTE] = {
            row.id: row.title
            for row in db.execute(
                select(MeetingNote.id, MeetingNote.title).where(
                    MeetingNote.workspace_id == workspace_id,
                    MeetingNote.deleted_at.is_(None),
                )
            ).all()
        }
    return result


def _semantic_search(
    db: Session,
    workspace_id: uuid.UUID,
    query: str,
    search_type: SearchType | None,
    limit: int,
) -> list[SearchResult]:
    if search_type == "task":
        return []
    titles = _active_source_titles(db, workspace_id, search_type)
    source_ids = [source_id for sources in titles.values() for source_id in sources]
    if not source_ids:
        return []
    filters = [Embedding.workspace_id == workspace_id, Embedding.source_id.in_(source_ids)]
    if search_type == "document":
        filters.append(Embedding.source_type == EmbeddingSourceType.DOCUMENT)
    elif search_type == "meeting_note":
        filters.append(Embedding.source_type == EmbeddingSourceType.MEETING_NOTE)
    embedding_count = db.scalar(select(func.count()).select_from(Embedding).where(*filters)) or 0
    if not embedding_count:
        return []

    try:
        query_vector = EmbeddingVector(values=get_ai_provider().generate_embedding(query)).values
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            distance = Embedding.embedding.op("<=>")(query_vector).label("distance")
            rows = db.execute(
                select(Embedding, distance)
                .where(*filters)
                .order_by(distance)
                .limit(limit)
            ).all()
            scored = [(embedding, 1.0 - float(value)) for embedding, value in rows]
        else:
            embeddings = db.scalars(select(Embedding).where(*filters)).all()
            scored = [(embedding, cosine_similarity(query_vector, embedding.embedding)) for embedding in embeddings]
            scored.sort(key=lambda item: (-item[1], str(item[0].id)))
            scored = scored[:limit]
    except (AIProviderError, ValidationError, ValueError, SQLAlchemyError) as exc:
        logger.error("Semantic search unavailable with %s; using text fallback", type(exc).__name__)
        db.rollback()
        return []

    results: list[SearchResult] = []
    for embedding, score in scored:
        title = titles.get(embedding.source_type, {}).get(embedding.source_id)
        if title is None:
            continue
        results.append(
            SearchResult(
                source_type=embedding.source_type.value.lower(),
                source_id=embedding.source_id,
                title=title,
                snippet=embedding.content_snippet[:350],
                score=round(score, 6),
                search_mode="semantic",
            )
        )
    return results


def _text_search(
    db: Session,
    workspace_id: uuid.UUID,
    query: str,
    search_type: SearchType | None,
    limit: int,
) -> list[SearchResult]:
    pattern = f"%{query}%"
    use_postgresql_fts = db.bind is not None and db.bind.dialect.name == "postgresql"
    results: list[SearchResult] = []
    if search_type in (None, "document"):
        if use_postgresql_fts:
            vector = func.to_tsvector(func.concat_ws(" ", Document.title, Document.content))
            ts_query = func.plainto_tsquery(query)
            rank = func.ts_rank(vector, ts_query).label("rank")
            document_rows = db.execute(
                select(Document, rank)
                .where(
                    Document.workspace_id == workspace_id,
                    Document.deleted_at.is_(None),
                    vector.op("@@")(ts_query),
                )
                .order_by(rank.desc(), Document.updated_at.desc())
                .limit(limit)
            ).all()
            documents = [(document, float(score), "full_text") for document, score in document_rows]
        else:
            documents = [
                (document, None, "text")
                for document in db.scalars(
                    select(Document)
                    .where(
                        Document.workspace_id == workspace_id,
                        Document.deleted_at.is_(None),
                        or_(Document.title.ilike(pattern), Document.content.ilike(pattern)),
                    )
                    .order_by(Document.updated_at.desc())
                    .limit(limit)
                ).all()
            ]
        results.extend(
            SearchResult(
                source_type="document",
                source_id=document.id,
                title=document.title,
                snippet=_snippet(document.content, query),
                score=round(score, 8) if score is not None else None,
                search_mode=mode,
            )
            for document, score, mode in documents
        )
    if search_type in (None, "meeting_note") and len(results) < limit:
        remaining = limit - len(results)
        if use_postgresql_fts:
            vector = func.to_tsvector(func.concat_ws(" ", MeetingNote.title, MeetingNote.content))
            ts_query = func.plainto_tsquery(query)
            rank = func.ts_rank(vector, ts_query).label("rank")
            note_rows = db.execute(
                select(MeetingNote, rank)
                .where(
                    MeetingNote.workspace_id == workspace_id,
                    MeetingNote.deleted_at.is_(None),
                    vector.op("@@")(ts_query),
                )
                .order_by(rank.desc(), MeetingNote.updated_at.desc())
                .limit(remaining)
            ).all()
            notes = [(note, float(score), "full_text") for note, score in note_rows]
        else:
            notes = [
                (note, None, "text")
                for note in db.scalars(
                    select(MeetingNote)
                    .where(
                        MeetingNote.workspace_id == workspace_id,
                        MeetingNote.deleted_at.is_(None),
                        or_(MeetingNote.title.ilike(pattern), MeetingNote.content.ilike(pattern)),
                    )
                    .order_by(MeetingNote.updated_at.desc())
                    .limit(remaining)
                ).all()
            ]
        results.extend(
            SearchResult(
                source_type="meeting_note",
                source_id=note.id,
                title=note.title,
                snippet=_snippet(note.content, query),
                score=round(score, 8) if score is not None else None,
                search_mode=mode,
            )
            for note, score, mode in notes
        )
    if search_type in (None, "task") and len(results) < limit:
        tasks = db.scalars(
            select(Task)
            .where(
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern)),
            )
            .order_by(Task.updated_at.desc())
            .limit(limit - len(results))
        ).all()
        results.extend(
            SearchResult(
                source_type="task",
                source_id=task.id,
                title=task.title,
                snippet=_snippet(task.description or task.title, query),
                search_mode="text",
            )
            for task in tasks
        )
    return results


def search_workspace(
    db: Session,
    workspace_id: uuid.UUID,
    query: str,
    search_type: SearchType | None,
    limit: int,
) -> tuple[str, list[SearchResult]]:
    semantic = _semantic_search(db, workspace_id, query, search_type, limit)
    if semantic:
        if search_type is None:
            task_results = _text_search(db, workspace_id, query, "task", max(0, limit - len(semantic)))
            if task_results:
                return "mixed", (semantic + task_results)[:limit]
        return "semantic", semantic
    fallback_results = _text_search(db, workspace_id, query, search_type, limit)
    result_modes = {item.search_mode for item in fallback_results}
    if "full_text" in result_modes:
        return ("mixed" if len(result_modes) > 1 else "full_text"), fallback_results
    return "text", fallback_results


def normalized_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def duplicate_task_suggestions(
    db: Session, workspace_id: uuid.UUID, limit: int = 20
) -> list[DuplicateTaskSuggestion]:
    tasks = db.scalars(
        select(Task)
        .where(Task.workspace_id == workspace_id, Task.deleted_at.is_(None))
        .order_by(Task.created_at.asc())
        .limit(1_000)
    ).all()
    suggestions: list[DuplicateTaskSuggestion] = []
    for index, first in enumerate(tasks):
        for second in tasks[index + 1 :]:
            first_title = normalized_title(first.title)
            second_title = normalized_title(second.title)
            if not first_title or not second_title:
                continue
            score = SequenceMatcher(None, first_title, second_title).ratio()
            if score < 0.72:
                continue
            suggestions.append(
                DuplicateTaskSuggestion(
                    task_id=first.id,
                    task_title=first.title,
                    duplicate_task_id=second.id,
                    duplicate_task_title=second.title,
                    similarity=round(score, 4),
                    reason=f"Titles are {round(score * 100)}% similar.",
                )
            )
    suggestions.sort(key=lambda item: (-item.similarity, str(item.task_id), str(item.duplicate_task_id)))
    return suggestions[:limit]
