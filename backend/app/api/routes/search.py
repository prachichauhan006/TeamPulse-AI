import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentMembership, DbSession, enforce_search_rate_limit
from app.schemas.search import DuplicateTaskSuggestionListResponse, SearchResponse
from app.services.search import duplicate_task_suggestions, search_workspace

router = APIRouter(
    prefix="/workspaces/{workspace_id}",
    tags=["search"],
    dependencies=[Depends(enforce_search_rate_limit)],
)


@router.get("/search", response_model=SearchResponse)
def search(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: CurrentMembership,
    q: str = Query(min_length=2, max_length=300),
    search_type: Literal["document", "meeting_note", "task"] | None = Query(default=None, alias="type"),
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    clean_query = q.strip()
    if len(clean_query) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Search query is blank")
    mode, items = search_workspace(db, workspace_id, clean_query, search_type, limit)
    return SearchResponse(query=clean_query, mode=mode, items=items)


@router.get("/duplicate-task-suggestions", response_model=DuplicateTaskSuggestionListResponse)
def duplicate_tasks(
    workspace_id: uuid.UUID, db: DbSession, membership: CurrentMembership
) -> DuplicateTaskSuggestionListResponse:
    return DuplicateTaskSuggestionListResponse(items=duplicate_task_suggestions(db, workspace_id))
