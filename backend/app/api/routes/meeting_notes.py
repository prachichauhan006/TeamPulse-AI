import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import func, select

from app.api.deps import CurrentMembership, CurrentUser, DbSession, enforce_ai_rate_limit, require_roles
from app.models.ai_proposal import AIProposal
from app.models.enums import EmbeddingSourceType, WorkspaceRole
from app.models.meeting_note import MeetingNote
from app.models.workspace import WorkspaceMember
from app.repositories.projects import get_project
from app.schemas.ai import AIProposalResponse
from app.schemas.meeting_note import (
    MeetingActionApprovalRequest,
    MeetingNoteCreate,
    MeetingNoteListResponse,
    MeetingNoteResponse,
)
from app.services.ai.base import AIProviderError
from app.services.ai_validation import AIResponseValidationError
from app.services.audit import add_audit_log, request_ip
from app.services.embeddings import schedule_source_embedding
from app.services.meeting_actions import (
    MeetingWorkflowError,
    approve_meeting_actions,
    generate_meeting_action_proposal,
)
from app.services.proposals import serialize_proposal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces/{workspace_id}/meeting-notes", tags=["meeting notes"])
MeetingEditors = Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER))


def get_note(db: DbSession, workspace_id: uuid.UUID, note_id: uuid.UUID) -> MeetingNote:
    note = db.scalar(
        select(MeetingNote).where(
            MeetingNote.id == note_id,
            MeetingNote.workspace_id == workspace_id,
            MeetingNote.deleted_at.is_(None),
        )
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting note not found")
    return note


@router.post("", response_model=MeetingNoteResponse, status_code=status.HTTP_201_CREATED)
def create_meeting_note(
    workspace_id: uuid.UUID,
    payload: MeetingNoteCreate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = MeetingEditors,
) -> MeetingNote:
    if payload.project_id is not None and get_project(db, workspace_id, payload.project_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is not in this workspace")
    note = MeetingNote(
        workspace_id=workspace_id,
        project_id=payload.project_id,
        title=payload.title,
        content=payload.content,
        created_by=current_user.id,
    )
    db.add(note)
    db.flush()
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="MEETING_NOTE_CREATED",
        entity_type="meeting_note",
        entity_id=note.id,
        metadata={"title": note.title},
        ip_address=request_ip(request),
    )
    db.commit()
    schedule_source_embedding(EmbeddingSourceType.MEETING_NOTE, note.id, workspace_id)
    db.refresh(note)
    return note


@router.get("", response_model=MeetingNoteListResponse)
def list_meeting_notes(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: CurrentMembership,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> MeetingNoteListResponse:
    filters = [MeetingNote.workspace_id == workspace_id, MeetingNote.deleted_at.is_(None)]
    total = db.scalar(select(func.count()).select_from(MeetingNote).where(*filters)) or 0
    notes = db.scalars(
        select(MeetingNote)
        .where(*filters)
        .order_by(MeetingNote.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return MeetingNoteListResponse(items=notes, total=total, page=page, page_size=page_size)


@router.get("/{meeting_note_id}", response_model=MeetingNoteResponse)
def read_meeting_note(
    workspace_id: uuid.UUID, meeting_note_id: uuid.UUID, db: DbSession, membership: CurrentMembership
) -> MeetingNote:
    return get_note(db, workspace_id, meeting_note_id)


@router.post(
    "/{meeting_note_id}/extract-actions",
    response_model=AIProposalResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_ai_rate_limit)],
)
def extract_actions(
    workspace_id: uuid.UUID,
    meeting_note_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = MeetingEditors,
) -> dict:
    note = get_note(db, workspace_id, meeting_note_id)
    try:
        proposal = generate_meeting_action_proposal(
            db, note=note, actor=current_user, ip_address=request_ip(request)
        )
    except AIProviderError as exc:
        logger.error("Meeting AI provider failed with %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider is unavailable. Please try again later.",
        ) from None
    except (ValidationError, AIResponseValidationError) as exc:
        logger.error("Meeting AI validation failed with %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid extraction. No data was changed.",
        ) from None
    return serialize_proposal(proposal)


@router.post(
    "/{meeting_note_id}/approve-actions",
    response_model=AIProposalResponse,
    dependencies=[Depends(enforce_ai_rate_limit)],
)
def approve_actions(
    workspace_id: uuid.UUID,
    meeting_note_id: uuid.UUID,
    payload: MeetingActionApprovalRequest,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = MeetingEditors,
) -> dict:
    note = get_note(db, workspace_id, meeting_note_id)
    proposal = db.scalar(
        select(AIProposal)
        .where(
            AIProposal.id == payload.proposal_id,
            AIProposal.workspace_id == workspace_id,
            AIProposal.meeting_note_id == meeting_note_id,
        )
        .with_for_update()
    )
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting action proposal not found")
    try:
        approved = approve_meeting_actions(
            db,
            note=note,
            proposal=proposal,
            selected_keys=payload.action_item_keys,
            requested_project_id=payload.project_id,
            actor=current_user,
            ip_address=request_ip(request),
        )
    except (MeetingWorkflowError, AIResponseValidationError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return serialize_proposal(approved)
