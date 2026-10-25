import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import RiskStatus, TaskPriority, TaskStatus
from app.schemas.common import ORMModel


class TaskCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=50_000)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task title cannot be blank")
        return value


class TaskUpdate(BaseModel):
    project_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=50_000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return TaskCreate.clean_title(value)


class TaskResponse(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee_id: uuid.UUID | None
    due_date: date | None
    created_by: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int


class DependencyCreate(BaseModel):
    depends_on_task_id: uuid.UUID


class DependencyResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    depends_on_task_id: uuid.UUID
    dependency_title: str
    dependency_status: TaskStatus
    dependency_due_date: date | None
    created_at: datetime


class TaskRiskResponse(BaseModel):
    task_id: uuid.UUID
    status: RiskStatus
    reasons: list[str]
