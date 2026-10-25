import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def add_audit_log(
    db: Session,
    *,
    action: str,
    entity_type: str,
    workspace_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    log = AuditLog(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
        ip_address=ip_address,
    )
    db.add(log)
    return log
