"""Idempotent placement-platform demo seed. Passwords come only from runtime configuration."""

import os
import uuid
from datetime import datetime, timedelta, timezone

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.enums import EmbeddingSourceType, TaskPriority, TaskStatus, WorkspaceRole
from app.models.meeting_note import MeetingNote
from app.models.project import Project
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.auth import validate_password_strength
from app.services.audit import add_audit_log
from app.services.embeddings import generate_source_embeddings

DEMO_WORKSPACE_NAME = "Placement Prep Team"
DEMO_PROJECT_TITLE = "Placement Preparation Platform"
DEMO_USERS = [
    ("SEED_OWNER_EMAIL", "owner.demo@teampulse.app", "Demo Owner", WorkspaceRole.OWNER),
    ("SEED_ADMIN_EMAIL", "admin.demo@teampulse.app", "Demo Admin", WorkspaceRole.ADMIN),
    ("SEED_MEMBER_EMAIL", "member.demo@teampulse.app", "Demo Member", WorkspaceRole.MEMBER),
    ("SEED_VIEWER_EMAIL", "viewer.demo@teampulse.app", "Demo Viewer", WorkspaceRole.VIEWER),
]
DEMO_TASK_TITLES = [
    "Design Platform Architecture",
    "Build Authentication",
    "Create Resume Builder",
    "Implement Job Tracker",
    "Build Placement Dashboard",
    "Add Interview Preparation",
    "Integrate Notifications",
    "Write Test Cases",
    "Deploy Application",
]
_EMAIL_ADAPTER = TypeAdapter(EmailStr)


def _seed_email(env_name: str, default: str) -> str:
    value = os.getenv(env_name, default).strip().lower()
    try:
        return str(_EMAIL_ADAPTER.validate_python(value))
    except ValidationError as exc:
        raise RuntimeError(f"{env_name} must contain a valid demo email address") from exc


def _get_or_create_user(db: Session, email: str, full_name: str, password_hash: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, full_name=full_name, password_hash=password_hash)
        db.add(user)
        db.flush()
    return user


def _audit_once(db: Session, *, workspace_id: uuid.UUID, user_id: uuid.UUID, action: str, entity_type: str, entity_id: uuid.UUID, metadata: dict | None = None) -> None:
    existing = db.scalar(select(AuditLog).where(AuditLog.workspace_id == workspace_id, AuditLog.action == action, AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id))
    if existing is None:
        add_audit_log(db, workspace_id=workspace_id, user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, metadata=metadata or {"source": "demo_seed"})


def run_seed() -> None:
    password = os.getenv("SEED_USER_PASSWORD", "")
    try:
        validate_password_strength(password)
    except ValueError as exc:
        raise RuntimeError("Set SEED_USER_PASSWORD to a strong development-only password") from exc
    shared_hash = hash_password(password)
    users: dict[str, User] = {}
    emails = {env_name: _seed_email(env_name, default) for env_name, default, _name, _role in DEMO_USERS}

    with SessionLocal() as db:
        for env_name, _default_email, full_name, _role in DEMO_USERS:
            email = emails[env_name]
            users[email] = _get_or_create_user(db, email, full_name, shared_hash)

        owner_email = emails["SEED_OWNER_EMAIL"]
        owner = users[owner_email]
        workspace = db.scalar(select(Workspace).join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id).where(Workspace.name == DEMO_WORKSPACE_NAME, WorkspaceMember.user_id == owner.id, Workspace.deleted_at.is_(None)))
        if workspace is None:
            workspace = Workspace(name=DEMO_WORKSPACE_NAME)
            db.add(workspace)
            db.flush()
            _audit_once(db, workspace_id=workspace.id, user_id=owner.id, action="WORKSPACE_CREATED", entity_type="workspace", entity_id=workspace.id)

        for env_name, _default_email, _full_name, role in DEMO_USERS:
            user = users[emails[env_name]]
            membership = db.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id, WorkspaceMember.user_id == user.id))
            if membership is None:
                membership = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=role)
                db.add(membership)
                db.flush()
                _audit_once(db, workspace_id=workspace.id, user_id=owner.id, action="WORKSPACE_MEMBER_ADDED", entity_type="workspace_member", entity_id=membership.id, metadata={"role": role.value, "source": "demo_seed"})

        project = db.scalar(select(Project).where(Project.workspace_id == workspace.id, Project.title == DEMO_PROJECT_TITLE, Project.deleted_at.is_(None)))
        if project is None:
            project = Project(workspace_id=workspace.id, title=DEMO_PROJECT_TITLE, description="A placement preparation platform for student profiles, resumes, job tracking, and interview readiness.", created_by=owner.id)
            db.add(project)
            db.flush()
            _audit_once(db, workspace_id=workspace.id, user_id=owner.id, action="PROJECT_CREATED", entity_type="project", entity_id=project.id)

        admin = users[emails["SEED_ADMIN_EMAIL"]]
        member = users[emails["SEED_MEMBER_EMAIL"]]
        today = datetime.now(timezone.utc).date()
        task_specs = [
            ("Design Platform Architecture", owner, TaskPriority.HIGH, TaskStatus.DONE, 1, "Define the platform modules, data boundaries, and delivery milestones."),
            ("Build Authentication", admin, TaskPriority.CRITICAL, TaskStatus.BLOCKED, 3, "Implement secure sign-in, workspace authorization, and account recovery."),
            ("Create Resume Builder", member, TaskPriority.HIGH, TaskStatus.TODO, 7, "Create structured resume sections, preview, and review-ready export content."),
            ("Implement Job Tracker", member, TaskPriority.HIGH, TaskStatus.IN_PROGRESS, 6, "Track opportunities, application stages, owners, and follow-up dates."),
            ("Build Placement Dashboard", owner, TaskPriority.HIGH, TaskStatus.TODO, 10, "Surface placement progress, upcoming deadlines, and actionable student metrics."),
            ("Add Interview Preparation", member, TaskPriority.MEDIUM, TaskStatus.TODO, 12, "Organize interview practice resources, question sets, and preparation checkpoints."),
            ("Integrate Notifications", admin, TaskPriority.MEDIUM, TaskStatus.TODO, 14, "Notify students about application changes, deadlines, and review outcomes."),
            ("Write Test Cases", admin, TaskPriority.HIGH, TaskStatus.TODO, 16, "Cover authentication, placement workflows, permissions, and critical integrations."),
            ("Deploy Application", owner, TaskPriority.MEDIUM, TaskStatus.TODO, 20, "Prepare a repeatable release, monitoring checklist, and rollback plan."),
        ]
        tasks: dict[str, Task] = {task.title: task for task in db.scalars(select(Task).where(Task.workspace_id == workspace.id, Task.project_id == project.id, Task.deleted_at.is_(None))).all()}
        for title, assignee, priority, status, due_offset, description in task_specs:
            if title not in tasks:
                task = Task(workspace_id=workspace.id, project_id=project.id, title=title, description=description, status=status, priority=priority, assignee_id=assignee.id, due_date=today + timedelta(days=due_offset), created_by=owner.id)
                db.add(task)
                db.flush()
                tasks[title] = task
                _audit_once(db, workspace_id=workspace.id, user_id=owner.id, action="TASK_CREATED", entity_type="task", entity_id=task.id, metadata={"source": "demo_seed"})

        dependency_specs = [
            ("Create Resume Builder", "Build Authentication"),
            ("Build Placement Dashboard", "Create Resume Builder"),
            ("Build Placement Dashboard", "Implement Job Tracker"),
        ]
        for task_title, prerequisite_title in dependency_specs:
            task = tasks[task_title]
            prerequisite = tasks[prerequisite_title]
            dependency = db.scalar(select(TaskDependency).where(TaskDependency.workspace_id == workspace.id, TaskDependency.task_id == task.id, TaskDependency.depends_on_task_id == prerequisite.id))
            if dependency is None:
                dependency = TaskDependency(workspace_id=workspace.id, task_id=task.id, depends_on_task_id=prerequisite.id)
                db.add(dependency)
                db.flush()
                _audit_once(db, workspace_id=workspace.id, user_id=owner.id, action="TASK_DEPENDENCY_ADDED", entity_type="task_dependency", entity_id=dependency.id, metadata={"source": "demo_seed"})

        note = db.scalar(select(MeetingNote).where(MeetingNote.workspace_id == workspace.id, MeetingNote.title == "Placement preparation sync", MeetingNote.deleted_at.is_(None)))
        if note is None:
            note = MeetingNote(workspace_id=workspace.id, project_id=project.id, title="Placement preparation sync", content="Decision: Prioritize the student placement dashboard after resume and job tracking workflows.\nAction: Resolve authentication blockers.\nAction: Review resume builder acceptance criteria.\nAction: Confirm job tracker stage definitions.", created_by=owner.id)
            db.add(note)
            db.flush()
            _audit_once(db, workspace_id=workspace.id, user_id=owner.id, action="MEETING_NOTE_CREATED", entity_type="meeting_note", entity_id=note.id)

        document = db.scalar(select(Document).where(Document.workspace_id == workspace.id, Document.title == "Placement Preparation Platform Runbook", Document.deleted_at.is_(None)))
        if document is None:
            document = Document(workspace_id=workspace.id, project_id=project.id, title="Placement Preparation Platform Runbook", filename="placement-preparation-platform-runbook.md", mime_type="text/markdown", size_bytes=0, content="# Placement Preparation Platform Runbook\n\nReview authentication, resume readiness, job application stages, dashboard metrics, and interview preparation before each release. Record blockers and review downstream dependency risk during the placement sync.", created_by=owner.id)
            document.size_bytes = len(document.content.encode("utf-8"))
            db.add(document)
            db.flush()
            _audit_once(db, workspace_id=workspace.id, user_id=owner.id, action="DOCUMENT_CREATED", entity_type="document", entity_id=document.id)

        _audit_once(db, workspace_id=workspace.id, user_id=owner.id, action="DEMO_SEED_READY", entity_type="workspace", entity_id=workspace.id, metadata={"project": DEMO_PROJECT_TITLE, "source": "demo_seed"})
        db.commit()
        workspace_id = workspace.id
        note_id = note.id
        document_id = document.id
        project_id = project.id

    # Seed deterministic demo embeddings directly so search works immediately;
    # normal API-created sources continue to use the Celery enqueue path.
    generate_source_embeddings(EmbeddingSourceType.MEETING_NOTE, note_id, workspace_id)
    generate_source_embeddings(EmbeddingSourceType.DOCUMENT, document_id, workspace_id)

    print(f"Demo seed ready: {DEMO_WORKSPACE_NAME} / {DEMO_PROJECT_TITLE}")
    print(f"Workspace ID: {workspace_id}; Project ID: {project_id}")
    print("Users: " + ", ".join(sorted(users)))
    print("The raw password was not printed; only Argon2 hashes are stored.")


if __name__ == "__main__":
    run_seed()
