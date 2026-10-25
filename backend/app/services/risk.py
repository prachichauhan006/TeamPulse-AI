import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ProjectHealth, RiskStatus, TaskStatus
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.schemas.project import ProjectHealthResponse
from app.schemas.task import TaskRiskResponse
from app.services.dependencies import get_dependency_tasks


def calculate_task_risk(
    task: Task,
    dependencies: list[Task],
    today: date | None = None,
) -> tuple[RiskStatus, list[str]]:
    today = today or datetime.now(timezone.utc).date()
    if task.status == TaskStatus.DONE:
        return RiskStatus.ON_TRACK, []

    reasons: list[str] = []
    is_blocked = task.status == TaskStatus.BLOCKED
    is_overdue = task.due_date is not None and task.due_date < today

    if is_blocked:
        reasons.append("Task is marked as blocked.")
    if is_overdue:
        reasons.append(f"Task is overdue (due {task.due_date.isoformat()}).")

    for dependency in dependencies:
        if dependency.status == TaskStatus.DONE:
            continue
        if dependency.status == TaskStatus.BLOCKED:
            reasons.append(f"Dependency '{dependency.title}' is blocked.")
        if dependency.due_date is not None and dependency.due_date < today:
            reasons.append(
                f"Dependency '{dependency.title}' is overdue (due {dependency.due_date.isoformat()})."
            )
        elif dependency.due_date is not None and today <= dependency.due_date <= today + timedelta(days=2):
            reasons.append(
                f"Dependency '{dependency.title}' is due within 2 days ({dependency.due_date.isoformat()})."
            )

    if is_blocked:
        status = RiskStatus.BLOCKED
    elif is_overdue:
        status = RiskStatus.OVERDUE
    elif reasons:
        status = RiskStatus.AT_RISK
    else:
        status = RiskStatus.ON_TRACK
    return status, reasons


def get_task_risk(db: Session, workspace_id: uuid.UUID, task: Task) -> TaskRiskResponse:
    dependencies = [
        dependency_task
        for _, dependency_task in get_dependency_tasks(db, workspace_id, task.id)
    ]
    status, reasons = calculate_task_risk(task, dependencies)
    return TaskRiskResponse(task_id=task.id, status=status, reasons=reasons)


def get_project_health(
    db: Session, workspace_id: uuid.UUID, project_id: uuid.UUID
) -> ProjectHealthResponse:
    tasks = list(
        db.scalars(
            select(Task).where(
                Task.workspace_id == workspace_id,
                Task.project_id == project_id,
                Task.deleted_at.is_(None),
            )
        ).all()
    )
    task_ids = [task.id for task in tasks]
    dependency_map: dict[uuid.UUID, list[Task]] = {task_id: [] for task_id in task_ids}
    if task_ids:
        rows = db.execute(
            select(TaskDependency.task_id, Task)
            .join(Task, Task.id == TaskDependency.depends_on_task_id)
            .where(
                TaskDependency.workspace_id == workspace_id,
                TaskDependency.task_id.in_(task_ids),
                Task.deleted_at.is_(None),
            )
        ).all()
        for source_task_id, dependency_task in rows:
            dependency_map[source_task_id].append(dependency_task)

    risks = [calculate_task_risk(task, dependency_map[task.id])[0] for task in tasks]
    blocked = risks.count(RiskStatus.BLOCKED)
    overdue = risks.count(RiskStatus.OVERDUE)
    at_risk = risks.count(RiskStatus.AT_RISK)
    health = (
        ProjectHealth.CRITICAL
        if blocked or overdue
        else ProjectHealth.AT_RISK
        if at_risk
        else ProjectHealth.ON_TRACK
    )
    return ProjectHealthResponse(
        project_id=project_id,
        health=health,
        total_tasks=len(tasks),
        completed_tasks=sum(task.status == TaskStatus.DONE for task in tasks),
        blocked_tasks=blocked,
        overdue_tasks=overdue,
        at_risk_tasks=at_risk,
    )
