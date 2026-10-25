import uuid

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.ai_proposal import AIProposal
from app.models.enums import AIProposalStatus, AIProposalType, ProjectStatus, TaskStatus
from app.models.project import Project
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.user import User
from app.services.ai.factory import get_ai_provider
from app.services.ai.schemas import AIPlanOutput
from app.services.ai_validation import validate_plan_output, workspace_ai_users
from app.services.audit import add_audit_log


class ProposalWorkflowError(ValueError):
    pass


def serialize_proposal(proposal: AIProposal) -> dict:
    return {
        "id": proposal.id,
        "workspace_id": proposal.workspace_id,
        "proposal_type": proposal.proposal_type,
        "status": proposal.status,
        "meeting_note_id": proposal.meeting_note_id,
        "payload": proposal.payload,
        "result": proposal.result_json,
        "created_by": proposal.created_by,
        "reviewed_by": proposal.reviewed_by,
        "reviewed_at": proposal.reviewed_at,
        "created_at": proposal.created_at,
        "updated_at": proposal.updated_at,
    }


def generate_plan_proposal(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    actor: User,
    brief: str,
    ip_address: str | None,
) -> AIProposal:
    users = workspace_ai_users(db, workspace_id)
    raw_plan = get_ai_provider().generate_plan(brief, users)
    plan = validate_plan_output(AIPlanOutput.model_validate(raw_plan), users)
    proposal = AIProposal(
        workspace_id=workspace_id,
        proposal_type=AIProposalType.PROJECT_PLAN,
        status=AIProposalStatus.PENDING,
        source_text=brief,
        payload=plan.model_dump(mode="json"),
        created_by=actor.id,
    )
    db.add(proposal)
    db.flush()
    add_audit_log(
        db,
        workspace_id=workspace_id,
        user_id=actor.id,
        action="AI_PLAN_PROPOSAL_CREATED",
        entity_type="ai_proposal",
        entity_id=proposal.id,
        metadata={"task_count": len(plan.tasks)},
        ip_address=ip_address,
    )
    db.commit()
    return proposal


def approve_plan_proposal(
    db: Session,
    *,
    proposal: AIProposal,
    actor: User,
    ip_address: str | None,
) -> AIProposal:
    if proposal.proposal_type != AIProposalType.PROJECT_PLAN:
        raise ProposalWorkflowError("Use the meeting-action approval endpoint for this proposal")
    if proposal.status == AIProposalStatus.APPROVED:
        return proposal
    if proposal.status == AIProposalStatus.REJECTED:
        raise ProposalWorkflowError("A rejected proposal cannot be approved")

    try:
        plan = AIPlanOutput.model_validate(proposal.payload)
    except ValidationError as exc:
        raise ProposalWorkflowError("Stored proposal data is invalid") from exc
    users = workspace_ai_users(db, proposal.workspace_id)
    plan = validate_plan_output(plan, users)

    project = Project(
        workspace_id=proposal.workspace_id,
        title=plan.project_title,
        description=plan.summary,
        status=ProjectStatus.ACTIVE,
        created_by=actor.id,
    )
    db.add(project)
    db.flush()

    task_ids: dict[str, uuid.UUID] = {}
    for item in plan.tasks:
        task = Task(
            workspace_id=proposal.workspace_id,
            project_id=project.id,
            title=item.title,
            description=item.description,
            status=TaskStatus.TODO,
            priority=item.priority,
            assignee_id=item.suggested_assignee_id,
            due_date=item.due_date,
            created_by=actor.id,
        )
        db.add(task)
        db.flush()
        task_ids[item.key] = task.id

    dependency_ids: list[str] = []
    for item in plan.tasks:
        for dependency_key in item.depends_on:
            dependency = TaskDependency(
                workspace_id=proposal.workspace_id,
                task_id=task_ids[item.key],
                depends_on_task_id=task_ids[dependency_key],
            )
            db.add(dependency)
            db.flush()
            dependency_ids.append(str(dependency.id))

    proposal.status = AIProposalStatus.APPROVED
    proposal.reviewed_by = actor.id
    proposal.reviewed_at = utcnow()
    proposal.result_json = {
        "project_id": str(project.id),
        "task_ids": {key: str(value) for key, value in task_ids.items()},
        "dependency_ids": dependency_ids,
    }
    add_audit_log(
        db,
        workspace_id=proposal.workspace_id,
        user_id=actor.id,
        action="AI_PLAN_PROPOSAL_APPROVED",
        entity_type="ai_proposal",
        entity_id=proposal.id,
        metadata={"project_id": str(project.id), "task_count": len(task_ids)},
        ip_address=ip_address,
    )
    db.commit()
    return proposal


def reject_proposal(
    db: Session,
    *,
    proposal: AIProposal,
    actor: User,
    ip_address: str | None,
) -> AIProposal:
    if proposal.status == AIProposalStatus.APPROVED:
        raise ProposalWorkflowError("An approved proposal cannot be rejected")
    if proposal.status == AIProposalStatus.REJECTED:
        return proposal
    proposal.status = AIProposalStatus.REJECTED
    proposal.reviewed_by = actor.id
    proposal.reviewed_at = utcnow()
    add_audit_log(
        db,
        workspace_id=proposal.workspace_id,
        user_id=actor.id,
        action="AI_PROPOSAL_REJECTED",
        entity_type="ai_proposal",
        entity_id=proposal.id,
        metadata={"proposal_type": proposal.proposal_type.value},
        ip_address=ip_address,
    )
    db.commit()
    return proposal
