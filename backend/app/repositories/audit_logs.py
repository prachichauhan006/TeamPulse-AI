import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def list_audit_logs(
    db: Session,
    workspace_id: uuid.UUID,
    page: int,
    page_size: int,
    action: str | None = None,
    entity_type: str | None = None,
) -> tuple[list[AuditLog], int]:
    filters = [AuditLog.workspace_id == workspace_id]
    if action:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
    items = list(
        db.scalars(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return items, total


def serialize_audit_log(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "workspace_id": log.workspace_id,
        "user_id": log.user_id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "metadata": log.metadata_json,
        "ip_address": log.ip_address,
        "created_at": log.created_at,
    }
