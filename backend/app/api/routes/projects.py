import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentMembership, CurrentUser, DbSession, require_roles
from app.db.base import utcnow
from app.models.enums import ProjectStatus, WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.workspace import WorkspaceMember
from app.repositories.projects import get_project, list_projects
from app.schemas.project import (
    ProjectCreate,
    ProjectHealthResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.audit import add_audit_log, request_ip
from app.services.risk import get_project_health

router = APIRouter(prefix="/workspaces/{workspace_id}/projects", tags=["projects"])
ProjectManagers = Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN))


def require_project(db: DbSession, workspace_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    project = get_project(db, workspace_id, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    workspace_id: uuid.UUID,
    payload: ProjectCreate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = ProjectManagers,
) -> Project:
    project = Project(workspace_id=workspace_id, created_by=current_user.id, **payload.model_dump())
    db.add(project)
    db.flush()
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="PROJECT_CREATED",
        entity_type="project",
        entity_id=project.id,
        metadata={"title": project.title},
        ip_address=request_ip(request),
    )
    db.commit()
    return project


@router.get("", response_model=ProjectListResponse)
def list_workspace_projects(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: CurrentMembership,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    project_status: ProjectStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=200),
) -> ProjectListResponse:
    items, total = list_projects(db, workspace_id, page, page_size, project_status, q)
    return ProjectListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_workspace_project(
    workspace_id: uuid.UUID, project_id: uuid.UUID, db: DbSession, membership: CurrentMembership
) -> Project:
    return require_project(db, workspace_id, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = ProjectManagers,
) -> Project:
    project = require_project(db, workspace_id, project_id)
    updates = payload.model_dump(exclude_unset=True)
    if any(field in updates and updates[field] is None for field in ("title", "description", "status")):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Project fields cannot be null")
    for field, value in updates.items():
        setattr(project, field, value)
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="PROJECT_UPDATED",
        entity_type="project",
        entity_id=project.id,
        metadata={"fields": sorted(updates)},
        ip_address=request_ip(request),
    )
    db.commit()
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = ProjectManagers,
) -> Response:
    project = require_project(db, workspace_id, project_id)
    active_tasks = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.workspace_id == workspace_id,
            Task.project_id == project_id,
            Task.deleted_at.is_(None),
        )
    )
    if active_tasks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delete or move all active tasks before deleting this project",
        )
    project.deleted_at = utcnow()
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="PROJECT_DELETED",
        entity_type="project",
        entity_id=project.id,
        metadata={"strategy": "soft_delete"},
        ip_address=request_ip(request),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/health", response_model=ProjectHealthResponse)
def project_health(
    workspace_id: uuid.UUID, project_id: uuid.UUID, db: DbSession, membership: CurrentMembership
) -> ProjectHealthResponse:
    require_project(db, workspace_id, project_id)
    return get_project_health(db, workspace_id, project_id)
