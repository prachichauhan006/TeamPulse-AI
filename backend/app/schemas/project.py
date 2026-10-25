import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ProjectHealth, ProjectStatus
from app.schemas.common import ORMModel


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=20_000)
    status: ProjectStatus = ProjectStatus.ACTIVE

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project title cannot be blank")
        return value


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=20_000)
    status: ProjectStatus | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return ProjectCreate.clean_title(value)


class ProjectResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    description: str
    status: ProjectStatus
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int


class ProjectHealthResponse(BaseModel):
    project_id: uuid.UUID
    health: ProjectHealth
    total_tasks: int
    completed_tasks: int
    blocked_tasks: int
    overdue_tasks: int
    at_risk_tasks: int
