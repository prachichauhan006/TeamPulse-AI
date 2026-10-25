from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

from app.services.ai.schemas import (
    AIPlanOutput,
    AIWorkspaceUser,
    MeetingExtractionOutput,
    WeeklySummaryOutput,
)


class AIProviderError(RuntimeError):
    """Safe provider failure suitable for internal handling."""


class TransientAIProviderError(AIProviderError):
    """A provider failure that may succeed after a bounded retry."""


class AIProvider(ABC):
    @abstractmethod
    def generate_plan(
        self, brief: str, workspace_users: Sequence[AIWorkspaceUser]
    ) -> AIPlanOutput:
        raise NotImplementedError

    @abstractmethod
    def extract_meeting_actions(
        self, meeting_notes: str, workspace_users: Sequence[AIWorkspaceUser]
    ) -> MeetingExtractionOutput:
        raise NotImplementedError

    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    def generate_weekly_summary(
        self, project_health: Mapping[str, Any], tasks: Sequence[Mapping[str, Any]]
    ) -> WeeklySummaryOutput:
        raise NotImplementedError
