import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.ai.schemas import (
    AIPlanOutput,
    AIWorkspaceUser,
    MeetingExtractionOutput,
)


class AIResponseValidationError(ValueError):
    pass


def workspace_ai_users(db: Session, workspace_id: uuid.UUID) -> list[AIWorkspaceUser]:
    users = db.scalars(
        select(User)
        .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
        .where(WorkspaceMember.workspace_id == workspace_id, User.is_active.is_(True))
        .order_by(User.full_name.asc(), User.id.asc())
    ).all()
    return [AIWorkspaceUser(id=user.id, full_name=user.full_name) for user in users]


def _validate_assignee(
    assignee_id: uuid.UUID | None,
    users: dict[uuid.UUID, AIWorkspaceUser],
) -> str | None:
    if assignee_id is None:
        return None
    if assignee_id not in users:
        raise AIResponseValidationError("AI suggested an assignee outside the workspace")
    return users[assignee_id].full_name


def validate_plan_output(
    plan: AIPlanOutput, workspace_users: Sequence[AIWorkspaceUser]
) -> AIPlanOutput:
    users = {user.id: user for user in workspace_users}
    keys = [task.key for task in plan.tasks]
    if len(set(keys)) != len(keys):
        raise AIResponseValidationError("AI returned duplicate task keys")
    known_keys = set(keys)
    graph: dict[str, list[str]] = {}
    for task in plan.tasks:
        task.suggested_assignee_name = _validate_assignee(task.suggested_assignee_id, users)
        if any(reference not in known_keys for reference in task.depends_on):
            raise AIResponseValidationError("AI returned an unknown task dependency")
        if task.key in task.depends_on:
            raise AIResponseValidationError("AI returned a self-dependency")
        if len(set(task.depends_on)) != len(task.depends_on):
            raise AIResponseValidationError("AI returned duplicate task dependencies")
        graph[task.key] = task.depends_on

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visiting:
            raise AIResponseValidationError("AI returned circular task dependencies")
        if key in visited:
            return
        visiting.add(key)
        for dependency in graph[key]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in graph:
        visit(key)
    return plan


def validate_meeting_output(
    extraction: MeetingExtractionOutput,
    workspace_users: Sequence[AIWorkspaceUser],
) -> MeetingExtractionOutput:
    users = {user.id: user for user in workspace_users}
    keys = [item.key for item in extraction.action_items]
    if len(set(keys)) != len(keys):
        raise AIResponseValidationError("AI returned duplicate action item keys")
    for item in extraction.action_items:
        item.suggested_assignee_name = _validate_assignee(item.suggested_assignee_id, users)
    return extraction
