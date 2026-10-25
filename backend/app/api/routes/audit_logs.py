import uuid

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_roles
from app.models.enums import WorkspaceRole
from app.models.workspace import WorkspaceMember
from app.repositories.audit_logs import list_audit_logs, serialize_audit_log
from app.schemas.audit_log import AuditLogListResponse

router = APIRouter(prefix="/workspaces/{workspace_id}/audit-logs", tags=["audit logs"])
AuditReaders = Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN))


@router.get("", response_model=AuditLogListResponse)
def get_audit_logs(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: WorkspaceMember = AuditReaders,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    action: str | None = Query(default=None, max_length=80),
    entity_type: str | None = Query(default=None, max_length=60),
) -> AuditLogListResponse:
    logs, total = list_audit_logs(db, workspace_id, page, page_size, action, entity_type)
    return AuditLogListResponse(
        items=[serialize_audit_log(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )
