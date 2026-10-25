import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import AIProposalStatus, AIProposalType


class AIPlanPreviewRequest(BaseModel):
    brief: str = Field(min_length=20, max_length=100_000)


class AIProposalResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    proposal_type: AIProposalType
    status: AIProposalStatus
    meeting_note_id: uuid.UUID | None
    payload: dict[str, Any]
    result: dict[str, Any] | None
    created_by: uuid.UUID
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AIProposalListResponse(BaseModel):
    items: list[AIProposalResponse]
    total: int
    page: int
    page_size: int
