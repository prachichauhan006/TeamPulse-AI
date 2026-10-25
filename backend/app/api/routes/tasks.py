import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentMembership, CurrentUser, DbSession, require_roles
from app.db.base import utcnow
from app.models.enums import TaskPriority, TaskStatus, WorkspaceRole
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.repositories.projects import get_project
from app.repositories.tasks import get_task, list_tasks
from app.schemas.task import (
    DependencyCreate,
    DependencyResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskRiskResponse,
    TaskUpdate,
)
from app.services.audit import add_audit_log, request_ip
from app.services.dependencies import get_dependency_tasks, would_create_cycle
from app.services.risk import get_task_risk

router = APIRouter(prefix="/workspaces/{workspace_id}/tasks", tags=["tasks"])
TaskEditors = Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER))
TaskManagers = Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN))


def require_task(db: DbSession, workspace_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    task = get_task(db, workspace_id, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def validate_task_relations(
    db: DbSession,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    assignee_id: uuid.UUID | None,
) -> None:
    if get_project(db, workspace_id, project_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is not in this workspace")
    if assignee_id is not None:
        assignee = db.scalar(
            select(WorkspaceMember)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == assignee_id,
                User.is_active.is_(True),
            )
        )
        if assignee is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee must be a workspace member")


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    workspace_id: uuid.UUID,
    payload: TaskCreate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = TaskEditors,
) -> Task:
    validate_task_relations(db, workspace_id, payload.project_id, payload.assignee_id)
    task = Task(workspace_id=workspace_id, created_by=current_user.id, **payload.model_dump())
    db.add(task)
    db.flush()
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="TASK_CREATED",
        entity_type="task",
        entity_id=task.id,
        metadata={"project_id": str(task.project_id), "title": task.title},
        ip_address=request_ip(request),
    )
    db.commit()
    return task


@router.get("", response_model=TaskListResponse)
def list_workspace_tasks(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: CurrentMembership,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    project_id: uuid.UUID | None = None,
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    priority: TaskPriority | None = None,
    assignee_id: uuid.UUID | None = None,
    q: str | None = Query(default=None, max_length=200),
) -> TaskListResponse:
    items, total = list_tasks(
        db, workspace_id, page, page_size, project_id, task_status, priority, assignee_id, q
    )
    return TaskListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{task_id}", response_model=TaskResponse)
def get_workspace_task(
    workspace_id: uuid.UUID, task_id: uuid.UUID, db: DbSession, membership: CurrentMembership
) -> Task:
    return require_task(db, workspace_id, task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    workspace_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskUpdate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = TaskEditors,
) -> Task:
    task = require_task(db, workspace_id, task_id)
    updates = payload.model_dump(exclude_unset=True)
    non_nullable = ("project_id", "title", "description", "status", "priority")
    if any(field in updates and updates[field] is None for field in non_nullable):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Required task fields cannot be null")
    project_id = updates.get("project_id", task.project_id)
    assignee_id = updates.get("assignee_id", task.assignee_id)
    validate_task_relations(db, workspace_id, project_id, assignee_id)
    for field, value in updates.items():
        setattr(task, field, value)
    task.version += 1
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="TASK_UPDATED",
        entity_type="task",
        entity_id=task.id,
        metadata={"fields": sorted(updates), "version": task.version},
        ip_address=request_ip(request),
    )
    db.commit()
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    workspace_id: uuid.UUID,
    task_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = TaskManagers,
) -> Response:
    task = require_task(db, workspace_id, task_id)
    task.deleted_at = utcnow()
    task.version += 1
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="TASK_DELETED",
        entity_type="task",
        entity_id=task.id,
        metadata={"strategy": "soft_delete"},
        ip_address=request_ip(request),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{task_id}/dependencies",
    response_model=DependencyResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_dependency(
    workspace_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: DependencyCreate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = TaskEditors,
) -> DependencyResponse:
    task = require_task(db, workspace_id, task_id)
    dependency_task = require_task(db, workspace_id, payload.depends_on_task_id)
    if task.id == dependency_task.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A task cannot depend on itself")
    existing = db.scalar(
        select(TaskDependency).where(
            TaskDependency.workspace_id == workspace_id,
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == dependency_task.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dependency already exists")
    if would_create_cycle(db, workspace_id, task.id, dependency_task.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dependency would create a cycle")
    dependency = TaskDependency(
        workspace_id=workspace_id,
        task_id=task.id,
        depends_on_task_id=dependency_task.id,
    )
    db.add(dependency)
    try:
        db.flush()
        add_audit_log(
            db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            action="TASK_DEPENDENCY_ADDED",
            entity_type="task_dependency",
            entity_id=dependency.id,
            metadata={"task_id": str(task.id), "depends_on_task_id": str(dependency_task.id)},
            ip_address=request_ip(request),
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dependency already exists or is invalid") from None
    return DependencyResponse(
        id=dependency.id,
        task_id=task.id,
        depends_on_task_id=dependency_task.id,
        dependency_title=dependency_task.title,
        dependency_status=dependency_task.status,
        dependency_due_date=dependency_task.due_date,
        created_at=dependency.created_at,
    )


@router.get("/{task_id}/dependencies", response_model=list[DependencyResponse])
def list_dependencies(
    workspace_id: uuid.UUID, task_id: uuid.UUID, db: DbSession, membership: CurrentMembership
) -> list[DependencyResponse]:
    require_task(db, workspace_id, task_id)
    rows = get_dependency_tasks(db, workspace_id, task_id)
    return [
        DependencyResponse(
            id=dependency.id,
            task_id=dependency.task_id,
            depends_on_task_id=dependency_task.id,
            dependency_title=dependency_task.title,
            dependency_status=dependency_task.status,
            dependency_due_date=dependency_task.due_date,
            created_at=dependency.created_at,
        )
        for dependency, dependency_task in rows
    ]


@router.delete("/{task_id}/dependencies/{depends_on_task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_dependency(
    workspace_id: uuid.UUID,
    task_id: uuid.UUID,
    depends_on_task_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = TaskEditors,
) -> Response:
    require_task(db, workspace_id, task_id)
    dependency = db.scalar(
        select(TaskDependency).where(
            TaskDependency.workspace_id == workspace_id,
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == depends_on_task_id,
        )
    )
    if dependency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dependency not found")
    db.delete(dependency)
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="TASK_DEPENDENCY_REMOVED",
        entity_type="task_dependency",
        entity_id=dependency.id,
        metadata={"task_id": str(task_id), "depends_on_task_id": str(depends_on_task_id)},
        ip_address=request_ip(request),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{task_id}/risk", response_model=TaskRiskResponse)
def task_risk(
    workspace_id: uuid.UUID, task_id: uuid.UUID, db: DbSession, membership: CurrentMembership
) -> TaskRiskResponse:
    task = require_task(db, workspace_id, task_id)
    return get_task_risk(db, workspace_id, task)
