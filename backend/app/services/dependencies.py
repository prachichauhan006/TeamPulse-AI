import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models.task import Task
from app.models.task_dependency import TaskDependency


def graph_would_create_cycle(
    adjacency: dict[uuid.UUID, list[uuid.UUID]],
    task_id: uuid.UUID,
    depends_on_task_id: uuid.UUID,
) -> bool:
    """Return whether task -> dependency would close a directed dependency cycle."""
    if task_id == depends_on_task_id:
        return True
    stack = [depends_on_task_id]
    visited: set[uuid.UUID] = set()
    while stack:
        current = stack.pop()
        if current == task_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        stack.extend(adjacency.get(current, []))
    return False


def workspace_dependency_graph(db: Session, workspace_id: uuid.UUID) -> dict[uuid.UUID, list[uuid.UUID]]:
    depended_task = aliased(Task)
    rows = db.execute(
        select(TaskDependency.task_id, TaskDependency.depends_on_task_id)
        .join(Task, Task.id == TaskDependency.task_id)
        .join(depended_task, depended_task.id == TaskDependency.depends_on_task_id)
        .where(
            TaskDependency.workspace_id == workspace_id,
            Task.deleted_at.is_(None),
            depended_task.deleted_at.is_(None),
        )
    ).all()
    graph: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for source_id, dependency_id in rows:
        graph[source_id].append(dependency_id)
    return dict(graph)


def would_create_cycle(
    db: Session,
    workspace_id: uuid.UUID,
    task_id: uuid.UUID,
    depends_on_task_id: uuid.UUID,
) -> bool:
    return graph_would_create_cycle(
        workspace_dependency_graph(db, workspace_id), task_id, depends_on_task_id
    )


def get_dependency_tasks(
    db: Session, workspace_id: uuid.UUID, task_id: uuid.UUID
) -> list[tuple[TaskDependency, Task]]:
    return list(
        db.execute(
            select(TaskDependency, Task)
            .join(Task, Task.id == TaskDependency.depends_on_task_id)
            .where(
                TaskDependency.workspace_id == workspace_id,
                TaskDependency.task_id == task_id,
                Task.deleted_at.is_(None),
            )
            .order_by(TaskDependency.created_at.asc())
        ).all()
    )
