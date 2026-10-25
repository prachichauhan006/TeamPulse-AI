import math
import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import EMBEDDING_DIMENSIONS
from app.models.enums import TaskPriority


class StrictAIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AIWorkspaceUser(StrictAIModel):
    id: uuid.UUID
    full_name: str = Field(min_length=1, max_length=120)


class AIPlanTask(StrictAIModel):
    key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10_000)
    priority: TaskPriority = TaskPriority.MEDIUM
    suggested_assignee_id: uuid.UUID | None = None
    suggested_assignee_name: str | None = Field(default=None, max_length=120)
    due_date: date | None = None
    depends_on: list[str] = Field(default_factory=list, max_length=20)


class AIPlanOutput(StrictAIModel):
    project_title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=10_000)
    tasks: list[AIPlanTask] = Field(min_length=1, max_length=30)
    risks: list[str] = Field(default_factory=list, max_length=20)
    assumptions: list[str] = Field(default_factory=list, max_length=20)


class MeetingActionItem(StrictAIModel):
    key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10_000)
    suggested_assignee_id: uuid.UUID | None = None
    suggested_assignee_name: str | None = Field(default=None, max_length=120)
    due_date: date | None = None


class MeetingExtractionOutput(StrictAIModel):
    summary: str = Field(min_length=1, max_length=10_000)
    decisions: list[str] = Field(default_factory=list, max_length=30)
    action_items: list[MeetingActionItem] = Field(default_factory=list, max_length=30)


class WeeklySummaryOutput(StrictAIModel):
    summary: str = Field(min_length=1, max_length=5_000)
    highlights: list[str] = Field(default_factory=list, max_length=20)
    recommended_actions: list[str] = Field(default_factory=list, max_length=20)


class EmbeddingVector(BaseModel):
    values: list[float] = Field(min_length=EMBEDDING_DIMENSIONS, max_length=EMBEDDING_DIMENSIONS)

    @field_validator("values")
    @classmethod
    def finite_values(cls, values: list[float]) -> list[float]:
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Embedding values must be finite")
        return values


class ProviderJSONResponse(BaseModel):
    """Internal wrapper used to validate that provider output is an object."""

    payload: dict[str, Any]
