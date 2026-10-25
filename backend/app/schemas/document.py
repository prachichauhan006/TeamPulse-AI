import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EmbeddingStatus


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    project_id: uuid.UUID | None = None

    @field_validator("title", "content")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Document title/content cannot be blank")
        return value


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    project_id: uuid.UUID | None
    title: str
    filename: str | None
    mime_type: str
    size_bytes: int
    embedding_status: EmbeddingStatus
    embedding_error: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DocumentResponse(DocumentListItem):
    content: str


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
    page: int
    page_size: int
