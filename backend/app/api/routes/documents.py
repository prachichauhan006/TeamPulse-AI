import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, select

from app.api.deps import CurrentMembership, CurrentUser, DbSession, require_roles
from app.core.config import get_settings
from app.db.base import utcnow
from app.models.document import Document
from app.models.enums import EmbeddingSourceType, EmbeddingStatus, WorkspaceRole
from app.models.workspace import WorkspaceMember
from app.repositories.projects import get_project
from app.schemas.document import DocumentCreate, DocumentListResponse, DocumentResponse
from app.services.audit import add_audit_log, request_ip
from app.services.documents import DocumentValidationError, read_upload_limited, sanitize_filename
from app.services.embeddings import schedule_source_embedding

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])
DocumentEditors = Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER))


def get_document(db: DbSession, workspace_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
            Document.deleted_at.is_(None),
        )
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def validate_size(content: str, max_bytes: int) -> int:
    size = len(content.encode("utf-8"))
    if size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Document exceeds the {max_bytes // (1024 * 1024)} MB upload limit",
        )
    return size


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    workspace_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = DocumentEditors,
    file: UploadFile | None = File(default=None),
    form_title: str | None = Form(default=None, alias="title"),
    form_content: str | None = Form(default=None, alias="content"),
    form_project_id: str | None = Form(default=None, alias="project_id"),
) -> Document:
    settings = get_settings()
    max_bytes = settings.document_max_upload_mb * 1024 * 1024
    filename: str | None = None
    mime_type = "text/plain"

    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            payload = DocumentCreate.model_validate(await request.json())
        except (ValidationError, ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid document payload") from None
        title, content, project_id = payload.title, payload.content, payload.project_id
    elif file is not None:
        filename = sanitize_filename(file.filename or "")
        suffix = Path(filename).suffix.lower()
        if suffix not in {".txt", ".md"}:
            await file.close()
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only .txt and .md files are supported",
            )
        try:
            raw_content = await read_upload_limited(file, max_bytes)
        except DocumentValidationError as exc:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from None
        finally:
            await file.close()
        try:
            content = raw_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Document must be UTF-8 text") from None
        try:
            payload = DocumentCreate(
                title=form_title or Path(filename).stem,
                content=content,
                project_id=form_project_id or None,
            )
        except ValidationError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid document content or title") from None
        title, project_id = payload.title, payload.project_id
        content = payload.content
        mime_type = "text/markdown" if suffix == ".md" else "text/plain"
    else:
        try:
            payload = DocumentCreate(
                title=form_title or "",
                content=form_content or "",
                project_id=form_project_id or None,
            )
        except ValidationError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide pasted text or a .txt/.md file",
            ) from None
        title, content, project_id = payload.title, payload.content, payload.project_id

    size_bytes = validate_size(content, max_bytes)
    if project_id is not None and get_project(db, workspace_id, project_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is not in this workspace")
    document = Document(
        workspace_id=workspace_id,
        project_id=project_id,
        title=title,
        filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        content=content,
        created_by=current_user.id,
    )
    db.add(document)
    db.flush()
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="DOCUMENT_CREATED",
        entity_type="document",
        entity_id=document.id,
        metadata={"title": document.title, "filename": document.filename, "size_bytes": size_bytes},
        ip_address=request_ip(request),
    )
    db.commit()
    schedule_source_embedding(EmbeddingSourceType.DOCUMENT, document.id, workspace_id)
    db.refresh(document)
    return document


@router.get("", response_model=DocumentListResponse)
def list_documents(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: CurrentMembership,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> DocumentListResponse:
    filters = [Document.workspace_id == workspace_id, Document.deleted_at.is_(None)]
    total = db.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
    documents = db.scalars(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return DocumentListResponse(items=documents, total=total, page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentResponse)
def read_document(
    workspace_id: uuid.UUID, document_id: uuid.UUID, db: DbSession, membership: CurrentMembership
) -> Document:
    return get_document(db, workspace_id, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = DocumentEditors,
) -> Response:
    document = get_document(db, workspace_id, document_id)
    document.deleted_at = utcnow()
    document.embedding_status = EmbeddingStatus.SKIPPED
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="DOCUMENT_DELETED",
        entity_type="document",
        entity_id=document.id,
        metadata={"strategy": "soft_delete"},
        ip_address=request_ip(request),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
