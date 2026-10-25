import uuid

from pydantic import BaseModel

class SearchResult(BaseModel):
    source_type: str
    source_id: uuid.UUID
    title: str
    snippet: str
    score: float | None = None
    search_mode: str


class SearchResponse(BaseModel):
    query: str
    mode: str
    items: list[SearchResult]


class DuplicateTaskSuggestion(BaseModel):
    task_id: uuid.UUID
    task_title: str
    duplicate_task_id: uuid.UUID
    duplicate_task_title: str
    similarity: float
    reason: str


class DuplicateTaskSuggestionListResponse(BaseModel):
    items: list[DuplicateTaskSuggestion]
