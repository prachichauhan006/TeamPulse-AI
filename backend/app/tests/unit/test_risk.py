from datetime import date, timedelta
from types import SimpleNamespace

from app.models.enums import RiskStatus, TaskStatus
from app.services.risk import calculate_task_risk

TODAY = date(2026, 10, 24)


def make_task(status=TaskStatus.TODO, due_date=None, title="Task"):
    return SimpleNamespace(status=status, due_date=due_date, title=title)


def test_blocked_task_has_blocked_risk():
    status, reasons = calculate_task_risk(make_task(status=TaskStatus.BLOCKED), [], TODAY)
    assert status == RiskStatus.BLOCKED
    assert "blocked" in reasons[0]


def test_incomplete_past_due_task_is_overdue():
    status, reasons = calculate_task_risk(make_task(due_date=TODAY - timedelta(days=1)), [], TODAY)
    assert status == RiskStatus.OVERDUE
    assert "overdue" in reasons[0]


def test_blocked_dependency_makes_downstream_task_at_risk():
    dependency = make_task(status=TaskStatus.BLOCKED, title="Backend API")
    status, reasons = calculate_task_risk(make_task(), [dependency], TODAY)
    assert status == RiskStatus.AT_RISK
    assert "Backend API" in reasons[0]


def test_overdue_dependency_and_near_deadline_are_explained():
    overdue = make_task(due_date=TODAY - timedelta(days=2), title="Overdue dependency")
    due_soon = make_task(due_date=TODAY + timedelta(days=2), title="Near deadline")
    status, reasons = calculate_task_risk(make_task(), [overdue, due_soon], TODAY)
    assert status == RiskStatus.AT_RISK
    assert len(reasons) == 2
    assert "overdue" in reasons[0]
    assert "within 2 days" in reasons[1]


def test_done_task_ignores_old_deadline_and_dependency_risks():
    blocked = make_task(status=TaskStatus.BLOCKED, title="Old dependency")
    status, reasons = calculate_task_risk(
        make_task(status=TaskStatus.DONE, due_date=TODAY - timedelta(days=30)),
        [blocked],
        TODAY,
    )
    assert status == RiskStatus.ON_TRACK
    assert reasons == []
