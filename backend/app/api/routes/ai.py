import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import func, select

from app.api.deps import CurrentMembership, CurrentUser, DbSession, enforce_ai_rate_limit, require_roles
from app.models.ai_proposal import AIProposal
from app.models.enums import AIProposalStatus, AIProposalType, ProjectHealth, WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.workspace import WorkspaceMember
from app.schemas.ai import AIPlanPreviewRequest, AIProposalListResponse, AIProposalResponse
from app.services.ai.base import AIProviderError
from app.services.ai.factory import get_ai_provider
from app.services.ai.schemas import WeeklySummaryOutput
from app.services.ai_validation import AIResponseValidationError
from app.services.audit import request_ip
from app.services.proposals import (
    ProposalWorkflowError,
    approve_plan_proposal,
    generate_plan_proposal,
    reject_proposal,
    serialize_proposal,
)
from app.services.risk import get_project_health

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/workspaces/{workspace_id}/ai",
    tags=["AI proposals"],
    dependencies=[Depends(enforce_ai_rate_limit)],
)
PlanManagers = Depends(require_roles(WorkspaceRole.OWNER, WorkspaceRole.ADMIN))


def get_proposal(
    db: DbSession, workspace_id: uuid.UUID, proposal_id: uuid.UUID, lock: bool = False
) -> AIProposal:
    statement = select(AIProposal).where(
        AIProposal.id == proposal_id, AIProposal.workspace_id == workspace_id
    )
    if lock:
        statement = statement.with_for_update()
    proposal = db.scalar(statement)
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI proposal not found")
    return proposal


@router.post("/plans/preview", response_model=AIProposalResponse, status_code=status.HTTP_201_CREATED)
def preview_plan(
    workspace_id: uuid.UUID,
    payload: AIPlanPreviewRequest,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = PlanManagers,
) -> dict:
    try:
        proposal = generate_plan_proposal(
            db,
            workspace_id=workspace_id,
            actor=current_user,
            brief=payload.brief,
            ip_address=request_ip(request),
        )
    except AIProviderError as exc:
        logger.error("AI plan provider failed with %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider is unavailable. Please try again later.",
        ) from None
    except (ValidationError, AIResponseValidationError) as exc:
        logger.error("AI plan validation failed with %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned an invalid proposal. No data was changed.",
        ) from None
    return serialize_proposal(proposal)


@router.get("/weekly-summary", response_model=WeeklySummaryOutput)
def weekly_summary(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: CurrentMembership,
) -> WeeklySummaryOutput:
    projects = db.scalars(
        select(Project).where(Project.workspace_id == workspace_id, Project.deleted_at.is_(None))
    ).all()
    health_values = [get_project_health(db, workspace_id, project.id).health for project in projects]
    overall_health = (
        ProjectHealth.CRITICAL
        if ProjectHealth.CRITICAL in health_values
        else ProjectHealth.AT_RISK
        if ProjectHealth.AT_RISK in health_values
        else ProjectHealth.ON_TRACK
    )
    tasks = db.scalars(
        select(Task)
        .where(Task.workspace_id == workspace_id, Task.deleted_at.is_(None))
        .order_by(Task.updated_at.desc())
        .limit(500)
    ).all()
    task_data = [
        {
            "title": task.title,
            "status": task.status.value,
            "priority": task.priority.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }
        for task in tasks
    ]
    try:
        return WeeklySummaryOutput.model_validate(
            get_ai_provider().generate_weekly_summary(
                {"health": overall_health.value}, task_data
            )
        )
    except (AIProviderError, ValidationError) as exc:
        logger.error("Weekly summary provider failed with %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI summary is temporarily unavailable. Please try again later.",
        ) from None


@router.get("/proposals", response_model=AIProposalListResponse)
def list_proposals(
    workspace_id: uuid.UUID,
    db: DbSession,
    membership: CurrentMembership,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    proposal_type: AIProposalType | None = Query(default=None, alias="type"),
    proposal_status: AIProposalStatus | None = Query(default=None, alias="status"),
) -> AIProposalListResponse:
    filters = [AIProposal.workspace_id == workspace_id]
    if proposal_type is not None:
        filters.append(AIProposal.proposal_type == proposal_type)
    if proposal_status is not None:
        filters.append(AIProposal.status == proposal_status)
    total = db.scalar(select(func.count()).select_from(AIProposal).where(*filters)) or 0
    proposals = db.scalars(
        select(AIProposal)
        .where(*filters)
        .order_by(AIProposal.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return AIProposalListResponse(
        items=[serialize_proposal(proposal) for proposal in proposals],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/proposals/{proposal_id}", response_model=AIProposalResponse)
def get_workspace_proposal(
    workspace_id: uuid.UUID,
    proposal_id: uuid.UUID,
    db: DbSession,
    membership: CurrentMembership,
) -> dict:
    return serialize_proposal(get_proposal(db, workspace_id, proposal_id))


@router.post("/proposals/{proposal_id}/approve", response_model=AIProposalResponse)
def approve_proposal(
    workspace_id: uuid.UUID,
    proposal_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = PlanManagers,
) -> dict:
    proposal = get_proposal(db, workspace_id, proposal_id, lock=True)
    try:
        approved = approve_plan_proposal(
            db, proposal=proposal, actor=current_user, ip_address=request_ip(request)
        )
    except ProposalWorkflowError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except AIResponseValidationError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Proposal assignees or dependencies are no longer valid. Generate a new preview.",
        ) from None
    return serialize_proposal(approved)


@router.post("/proposals/{proposal_id}/reject", response_model=AIProposalResponse)
def reject_workspace_proposal(
    workspace_id: uuid.UUID,
    proposal_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    membership: WorkspaceMember = PlanManagers,
) -> dict:
    proposal = get_proposal(db, workspace_id, proposal_id, lock=True)
    try:
        rejected = reject_proposal(
            db, proposal=proposal, actor=current_user, ip_address=request_ip(request)
        )
    except ProposalWorkflowError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return serialize_proposal(rejected)
