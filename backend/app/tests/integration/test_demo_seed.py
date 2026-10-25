from sqlalchemy import func, select

from app.db.seed import DEMO_PROJECT_TITLE, DEMO_TASK_TITLES, DEMO_WORKSPACE_NAME, run_seed
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.meeting_note import MeetingNote
from app.models.project import Project
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.tests.utils import TEST_PASSWORD


def test_demo_seed_is_rich_and_idempotent(monkeypatch):
    monkeypatch.setenv("SEED_USER_PASSWORD", TEST_PASSWORD)
    run_seed()
    run_seed()

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 4
        workspace = db.scalar(select(Workspace).where(Workspace.name == DEMO_WORKSPACE_NAME))
        assert workspace is not None
        memberships = db.scalars(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)).all()
        assert {member.role.value for member in memberships} == {"OWNER", "ADMIN", "MEMBER", "VIEWER"}
        assert db.scalar(select(User).where(User.email == "owner.demo@teampulse.app")) is not None
        project = db.scalar(select(Project).where(Project.title == DEMO_PROJECT_TITLE))
        assert project is not None
        tasks = db.scalars(select(Task).where(Task.project_id == project.id)).all()
        assert len(tasks) == 9
        assert {task.title for task in tasks} == set(DEMO_TASK_TITLES)
        assert all(task.title == task.title.title() for task in tasks)
        dependencies = db.scalars(select(TaskDependency)).all()
        assert len(dependencies) == 3
        by_title = {task.title: task for task in tasks}
        authentication = by_title["Build Authentication"]
        resume = by_title["Create Resume Builder"]
        dashboard = by_title["Build Placement Dashboard"]
        tracker = by_title["Implement Job Tracker"]
        assert authentication.status.value == "BLOCKED"
        assert {(dependency.task_id, dependency.depends_on_task_id) for dependency in dependencies} == {
            (resume.id, authentication.id),
            (dashboard.id, resume.id),
            (dashboard.id, tracker.id),
        }
        assert db.scalar(select(func.count()).select_from(MeetingNote)) == 1
        assert db.scalar(select(func.count()).select_from(Document)) == 1
        assert db.scalar(select(func.count()).select_from(AuditLog)) >= 8
