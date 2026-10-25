import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import ProjectStatus
from app.models.project import Project


def get_project(db: Session, workspace_id: uuid.UUID, project_id: uuid.UUID) -> Project | None:
    return db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
            Project.deleted_at.is_(None),
        )
    )


def list_projects(
    db: Session,
    workspace_id: uuid.UUID,
    page: int,
    page_size: int,
    status: ProjectStatus | None = None,
    query: str | None = None,
) -> tuple[list[Project], int]:
    filters = [Project.workspace_id == workspace_id, Project.deleted_at.is_(None)]
    if status is not None:
        filters.append(Project.status == status)
    if query:
        pattern = f"%{query.strip()}%"
        filters.append(or_(Project.title.ilike(pattern), Project.description.ilike(pattern)))
    total = db.scalar(select(func.count()).select_from(Project).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Project)
            .where(*filters)
            .order_by(Project.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return items, total
