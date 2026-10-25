import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EmbeddingStatus


class MeetingNoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=200_000)
    project_id: uuid.UUID | None = None

    @field_validator("title", "content")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be blank")
        return value


class MeetingNoteListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    project_id: uuid.UUID | None
    title: str
    embedding_status: EmbeddingStatus
    embedding_error: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class MeetingNoteResponse(MeetingNoteListItem):
    content: str


class MeetingNoteListResponse(BaseModel):
    items: list[MeetingNoteListItem]
    total: int
    page: int
    page_size: int


class MeetingActionApprovalRequest(BaseModel):
    proposal_id: uuid.UUID
    action_item_keys: list[str] = Field(min_length=1, max_length=30)
    project_id: uuid.UUID | None = None

    @field_validator("action_item_keys")
    @classmethod
    def unique_keys(cls, keys: list[str]) -> list[str]:
        if len(set(keys)) != len(keys):
            raise ValueError("Action item keys must be unique")
        return keys
