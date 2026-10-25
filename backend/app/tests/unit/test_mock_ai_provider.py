import math
import uuid

from app.services.ai.mock import MockAIProvider
from app.services.ai.schemas import AIWorkspaceUser

USERS = [
    AIWorkspaceUser(id=uuid.UUID(int=1), full_name="Alpha Owner"),
    AIWorkspaceUser(id=uuid.UUID(int=2), full_name="Beta Member"),
]


def test_mock_plan_is_deterministic_and_realistic():
    provider = MockAIProvider()
    brief = "Launch our customer portal with authentication, billing, and a rollout review."
    first = provider.generate_plan(brief, USERS)
    second = provider.generate_plan(brief, USERS)
    assert first == second
    assert first.project_title.startswith("Launch our customer portal")
    assert len(first.tasks) == 4
    assert first.tasks[1].depends_on == ["task-1"]
    assert first.tasks[2].depends_on == ["task-2"]
    assert first.tasks[3].depends_on == ["task-3"]
    assert first.tasks[0].suggested_assignee_id in {user.id for user in USERS}
    assert len({task.description for task in first.tasks}) == 4
    assert all(brief not in task.description for task in first.tasks)
    assert "mock" not in first.summary.lower()
    assert first.risks and first.assumptions


def test_mock_meeting_extraction_is_deterministic():
    provider = MockAIProvider()
    notes = "Decision: Launch Friday\nAction: Prepare release notes\nAction: Verify deployment"
    first = provider.extract_meeting_actions(notes, USERS)
    second = provider.extract_meeting_actions(notes, USERS)
    assert first == second
    assert first.decisions == ["Launch Friday"]
    assert [item.title for item in first.action_items] == ["Prepare release notes", "Verify deployment"]
    assert first.summary.startswith("Meeting summary:")
    assert "mock" not in first.summary.lower()


def test_mock_embeddings_are_stable_normalized_and_exactly_1536_dimensional():
    provider = MockAIProvider()
    first = provider.generate_embedding("Deployment checklist deployment owners")
    second = provider.generate_embedding("Deployment checklist deployment owners")
    different = provider.generate_embedding("Unrelated billing invoice")
    assert len(first) == 1536
    assert first == second
    assert first != different
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0, rel_tol=1e-6)


def test_mock_weekly_summary_is_deterministic():
    provider = MockAIProvider()
    health = {"health": "AT_RISK"}
    tasks = [{"status": "DONE"}, {"status": "BLOCKED"}, {"status": "TODO"}]
    first = provider.generate_weekly_summary(health, tasks)
    assert first == provider.generate_weekly_summary(health, tasks)
    assert "AT_RISK" in first.summary
    assert "1 of 3" in first.summary
    assert first.summary.startswith("Weekly project summary:")
    assert "mock" not in first.summary.lower()
