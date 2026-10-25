import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task


def get_task(db: Session, workspace_id: uuid.UUID, task_id: uuid.UUID) -> Task | None:
    return db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.workspace_id == workspace_id,
            Task.deleted_at.is_(None),
        )
    )


def list_tasks(
    db: Session,
    workspace_id: uuid.UUID,
    page: int,
    page_size: int,
    project_id: uuid.UUID | None = None,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: uuid.UUID | None = None,
    query: str | None = None,
) -> tuple[list[Task], int]:
    filters = [Task.workspace_id == workspace_id, Task.deleted_at.is_(None)]
    if project_id is not None:
        filters.append(Task.project_id == project_id)
    if status is not None:
        filters.append(Task.status == status)
    if priority is not None:
        filters.append(Task.priority == priority)
    if assignee_id is not None:
        filters.append(Task.assignee_id == assignee_id)
    if query:
        pattern = f"%{query.strip()}%"
        filters.append(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
    total = db.scalar(select(func.count()).select_from(Task).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Task)
            .where(*filters)
            .order_by(Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return items, total
