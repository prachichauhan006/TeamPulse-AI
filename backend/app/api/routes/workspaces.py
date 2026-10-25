import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentMembership, CurrentUser, DbSession, require_roles
from app.core.permissions import can_grant_role, can_manage_member
from app.db.base import utcnow
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.workspace import (
    MemberAddRequest,
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceDeleteRequest,
    WorkspaceMemberListResponse,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.audit import add_audit_log, request_ip

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
Administrators = Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN))
Owners = Depends(require_roles(WorkspaceRole.OWNER))


def get_active_workspace(db: DbSession, workspace_id: uuid.UUID) -> Workspace:
    workspace = db.scalar(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.deleted_at.is_(None))
    )
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


def serialize_member(member: WorkspaceMember, user: User) -> WorkspaceMemberResponse:
    return WorkspaceMemberResponse(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate, request: Request, db: DbSession, current_user: CurrentUser
) -> Workspace:
    workspace = Workspace(name=payload.name)
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=current_user.id, role=WorkspaceRole.OWNER))
    add_audit_log(
        db,
        workspace_id=workspace.id,
        user_id=current_user.id,
        action="WORKSPACE_CREATED",
        entity_type="workspace",
        entity_id=workspace.id,
        metadata={"name": workspace.name},
        ip_address=request_ip(request),
    )
    db.commit()
    return workspace


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(db: DbSession, current_user: CurrentUser) -> list[Workspace]:
    return list(
        db.scalars(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == current_user.id,
                Workspace.deleted_at.is_(None),
            )
            .order_by(Workspace.created_at.desc())
        ).all()
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: uuid.UUID, db: DbSession, membership: CurrentMembership) -> Workspace:
    return get_active_workspace(db, workspace_id)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = Administrators,
) -> Workspace:
    workspace = get_active_workspace(db, workspace_id)
    workspace.name = payload.name
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="WORKSPACE_UPDATED",
        entity_type="workspace",
        entity_id=workspace_id,
        metadata={"name": workspace.name},
        ip_address=request_ip(request),
    )
    db.commit()
    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceDeleteRequest,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = Owners,
) -> Response:
    workspace = get_active_workspace(db, workspace_id)
    if payload.confirmation != workspace.name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confirmation must exactly match the workspace name",
        )
    workspace.deleted_at = utcnow()
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="WORKSPACE_DELETED",
        entity_type="workspace",
        entity_id=workspace_id,
        metadata={"strategy": "soft_delete"},
        ip_address=request_ip(request),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{workspace_id}/members", response_model=WorkspaceMemberListResponse)
def list_members(workspace_id: uuid.UUID, db: DbSession, membership: CurrentMembership) -> WorkspaceMemberListResponse:
    rows = db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.created_at.asc())
    ).all()
    items = [serialize_member(member, user) for member, user in rows]
    return WorkspaceMemberListResponse(items=items, total=len(items))


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    workspace_id: uuid.UUID,
    payload: MemberAddRequest,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = Administrators,
) -> WorkspaceMemberResponse:
    if not can_grant_role(membership.role, payload.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot grant a role above your own")
    user = db.scalar(select(User).where(User.email == str(payload.email).lower(), User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registered user not found")
    existing = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a workspace member")
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=payload.role)
    db.add(member)
    db.flush()
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="WORKSPACE_MEMBER_ADDED",
        entity_type="workspace_member",
        entity_id=member.id,
        metadata={"target_user_id": str(user.id), "role": payload.role.value},
        ip_address=request_ip(request),
    )
    db.commit()
    return serialize_member(member, user)


@router.patch("/{workspace_id}/members/{user_id}", response_model=WorkspaceMemberResponse)
def update_member_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = Administrators,
) -> WorkspaceMemberResponse:
    row = db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found")
    target, user = row
    if not can_manage_member(membership.role, target.role) or not can_grant_role(membership.role, payload.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient member-management permissions")
    if target.role == WorkspaceRole.OWNER and payload.role != WorkspaceRole.OWNER:
        owner_count = db.scalar(
            select(func.count()).select_from(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == WorkspaceRole.OWNER,
            )
        )
        if owner_count == 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot demote the last workspace owner")
    target.role = payload.role
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="WORKSPACE_MEMBER_ROLE_UPDATED",
        entity_type="workspace_member",
        entity_id=target.id,
        metadata={"target_user_id": str(user_id), "role": payload.role.value},
        ip_address=request_ip(request),
    )
    db.commit()
    return serialize_member(target, user)


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = Administrators,
) -> Response:
    target = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found")
    if not can_manage_member(membership.role, target.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient member-management permissions")
    if target.role == WorkspaceRole.OWNER:
        owner_count = db.scalar(
            select(func.count()).select_from(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == WorkspaceRole.OWNER,
            )
        )
        if owner_count == 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot remove the last workspace owner")
    db.delete(target)
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="WORKSPACE_MEMBER_REMOVED",
        entity_type="workspace_member",
        entity_id=target.id,
        metadata={"target_user_id": str(user_id)},
        ip_address=request_ip(request),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
