import uuid

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.ai_proposal import AIProposal
from app.models.enums import AIProposalStatus, AIProposalType, TaskPriority, TaskStatus
from app.models.meeting_note import MeetingNote
from app.models.task import Task
from app.models.user import User
from app.repositories.projects import get_project
from app.services.ai.factory import get_ai_provider
from app.services.ai.schemas import MeetingExtractionOutput
from app.services.ai_validation import validate_meeting_output, workspace_ai_users
from app.services.audit import add_audit_log


class MeetingWorkflowError(ValueError):
    pass


def generate_meeting_action_proposal(
    db: Session,
    *,
    note: MeetingNote,
    actor: User,
    ip_address: str | None,
) -> AIProposal:
    users = workspace_ai_users(db, note.workspace_id)
    raw_extraction = get_ai_provider().extract_meeting_actions(note.content, users)
    extraction = validate_meeting_output(
        MeetingExtractionOutput.model_validate(raw_extraction), users
    )
    proposal = AIProposal(
        workspace_id=note.workspace_id,
        proposal_type=AIProposalType.MEETING_ACTIONS,
        status=AIProposalStatus.PENDING,
        meeting_note_id=note.id,
        payload=extraction.model_dump(mode="json"),
        created_by=actor.id,
    )
    db.add(proposal)
    db.flush()
    add_audit_log(
        db,
        workspace_id=note.workspace_id,
        user_id=actor.id,
        action="MEETING_ACTIONS_EXTRACTED",
        entity_type="ai_proposal",
        entity_id=proposal.id,
        metadata={"meeting_note_id": str(note.id), "action_count": len(extraction.action_items)},
        ip_address=ip_address,
    )
    db.commit()
    return proposal


def approve_meeting_actions(
    db: Session,
    *,
    note: MeetingNote,
    proposal: AIProposal,
    selected_keys: list[str],
    requested_project_id: uuid.UUID | None,
    actor: User,
    ip_address: str | None,
) -> AIProposal:
    if proposal.proposal_type != AIProposalType.MEETING_ACTIONS or proposal.meeting_note_id != note.id:
        raise MeetingWorkflowError("Proposal does not belong to this meeting note")
    if proposal.status == AIProposalStatus.APPROVED:
        return proposal
    if proposal.status == AIProposalStatus.REJECTED:
        raise MeetingWorkflowError("A rejected proposal cannot be approved")

    project_id = requested_project_id or note.project_id
    if project_id is None or get_project(db, note.workspace_id, project_id) is None:
        raise MeetingWorkflowError("Select a valid project in this workspace")
    try:
        extraction = MeetingExtractionOutput.model_validate(proposal.payload)
    except ValidationError as exc:
        raise MeetingWorkflowError("Stored meeting extraction is invalid") from exc
    extraction = validate_meeting_output(extraction, workspace_ai_users(db, note.workspace_id))

    selected = set(selected_keys)
    known_keys = {item.key for item in extraction.action_items}
    if not selected.issubset(known_keys):
        raise MeetingWorkflowError("Selection contains an unknown action item")

    created_task_ids: dict[str, str] = {}
    approved_keys: list[str] = []
    for item in extraction.action_items:
        if item.key not in selected:
            continue
        task = Task(
            workspace_id=note.workspace_id,
            project_id=project_id,
            title=item.title,
            description=item.description,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee_id=item.suggested_assignee_id,
            due_date=item.due_date,
            created_by=actor.id,
        )
        db.add(task)
        db.flush()
        created_task_ids[item.key] = str(task.id)
        approved_keys.append(item.key)

    proposal.status = AIProposalStatus.APPROVED
    proposal.reviewed_by = actor.id
    proposal.reviewed_at = utcnow()
    proposal.result_json = {
        "project_id": str(project_id),
        "task_ids": created_task_ids,
        "selected_action_item_keys": approved_keys,
    }
    add_audit_log(
        db,
        workspace_id=note.workspace_id,
        user_id=actor.id,
        action="MEETING_ACTIONS_APPROVED",
        entity_type="ai_proposal",
        entity_id=proposal.id,
        metadata={"meeting_note_id": str(note.id), "task_count": len(created_task_ids)},
        ip_address=ip_address,
    )
    db.commit()
    return proposal
