import hashlib
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from app.models.enums import TaskPriority
from app.services.ai.base import AIProvider
from app.services.ai.schemas import (
    EMBEDDING_DIMENSIONS,
    AIPlanOutput,
    AIPlanTask,
    AIWorkspaceUser,
    EmbeddingVector,
    MeetingActionItem,
    MeetingExtractionOutput,
    WeeklySummaryOutput,
)

MOCK_DATE_ANCHOR = date(2027, 1, 4)


def _excerpt(text: str, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    return cleaned[:limit] if cleaned else "No additional context provided."


def _owner(users: Sequence[AIWorkspaceUser], index: int) -> AIWorkspaceUser | None:
    return users[index % len(users)] if users else None


class MockAIProvider(AIProvider):
    """Offline deterministic provider for development, demos, and tests."""

    def generate_plan(
        self, brief: str, workspace_users: Sequence[AIWorkspaceUser]
    ) -> AIPlanOutput:
        first_line = next((line.strip() for line in brief.splitlines() if line.strip()), "Team project")
        project_title = first_line[:70].strip(" .:-") or "Team project"
        templates = [
            ("Define Placement Platform Scope", "Confirm student, recruiter, and coordinator workflows, success measures, and release boundaries.", TaskPriority.HIGH, []),
            ("Build Profiles And Resume Workflow", "Implement student profiles, resume details, and review checkpoints with workspace-safe ownership.", TaskPriority.HIGH, ["task-1"]),
            ("Implement Job Application Tracking", "Create application stages, ownership, and status history for placement opportunities.", TaskPriority.MEDIUM, ["task-2"]),
            ("Prepare Placement Dashboard Release", "Validate dashboard metrics, permissions, accessibility, and rollout readiness with the team.", TaskPriority.MEDIUM, ["task-3"]),
        ]
        tasks = []
        for index, (title, description, priority, dependencies) in enumerate(templates):
            owner = _owner(workspace_users, index)
            tasks.append(
                AIPlanTask(
                    key=f"task-{index + 1}",
                    title=title,
                    description=description,
                    priority=priority,
                    suggested_assignee_id=owner.id if owner else None,
                    suggested_assignee_name=owner.full_name if owner else None,
                    due_date=MOCK_DATE_ANCHOR + timedelta(days=index * 3 + 2),
                    depends_on=dependencies,
                )
            )
        return AIPlanOutput(
            project_title=project_title,
            summary=f"Placement preparation plan for {_excerpt(brief, 120)}",
            tasks=tasks,
            risks=[
                "Authentication or profile delays can block the resume and dashboard delivery sequence.",
                "Placement metrics may be misleading if application stages and ownership are not consistently defined.",
            ],
            assumptions=[
                "Workspace members listed as suggested owners are available for review and delivery.",
                "The placement workflow has agreed roles, application stages, and success measures.",
            ],
        )

    def extract_meeting_actions(
        self, meeting_notes: str, workspace_users: Sequence[AIWorkspaceUser]
    ) -> MeetingExtractionOutput:
        lines = [line.strip() for line in meeting_notes.splitlines() if line.strip()]
        decisions = [
            re.sub(r"^(?:decision|decided)\s*[:\-]\s*", "", line, flags=re.IGNORECASE)
            for line in lines
            if re.match(r"^(?:decision|decided)\s*[:\-]", line, flags=re.IGNORECASE)
        ]
        candidates = [
            re.sub(r"^(?:[-*]\s+|action\s*[:\-]\s*|todo\s*[:\-]\s*)", "", line, flags=re.IGNORECASE)
            for line in lines
            if re.match(r"^(?:[-*]|action\s*[:\-]|todo\s*[:\-])", line, flags=re.IGNORECASE)
        ]
        candidates = [candidate.strip() for candidate in candidates if candidate.strip()]
        if not candidates:
            candidates = ["Review the meeting notes and confirm follow-up owners."]
        actions = []
        for index, title in enumerate(candidates[:10]):
            owner = _owner(workspace_users, index)
            actions.append(
                MeetingActionItem(
                    key=f"action-{index + 1}",
                    title=title[:200],
                    description=f"Follow up on the agreed action: {title[:160]}",
                    suggested_assignee_id=owner.id if owner else None,
                    suggested_assignee_name=owner.full_name if owner else None,
                    due_date=MOCK_DATE_ANCHOR + timedelta(days=index + 1),
                )
            )
        return MeetingExtractionOutput(
            summary=f"Meeting summary: {_excerpt(meeting_notes)}",
            decisions=decisions,
            action_items=actions,
        )

    def generate_embedding(self, text: str) -> list[float]:
        # A deterministic hashing-trick vector preserves lexical overlap while
        # requiring no model download, network access, or random state.
        tokens = re.findall(r"[a-z0-9]+", text.lower()) or ["empty"]
        counts = Counter(tokens)
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for token, count in counts.items():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        normalized = [round(value / norm, 8) for value in vector]
        return EmbeddingVector(values=normalized).values

    def generate_weekly_summary(
        self, project_health: Mapping[str, Any], tasks: Sequence[Mapping[str, Any]]
    ) -> WeeklySummaryOutput:
        status_counts = Counter(str(task.get("status", "UNKNOWN")) for task in tasks)
        health = str(project_health.get("health", "UNKNOWN"))
        blocked = status_counts.get("BLOCKED", 0)
        done = status_counts.get("DONE", 0)
        return WeeklySummaryOutput(
            summary=f"Weekly project summary: project health is {health}; {done} of {len(tasks)} tasks are complete.",
            highlights=[f"{status}: {count} task(s)" for status, count in sorted(status_counts.items())],
            recommended_actions=[
                f"Review {blocked} blocked task(s) with their owners." if blocked else "Review upcoming dependencies and confirm owners."
            ],
        )
