from datetime import date

from app.tests.utils import create_project, create_task, create_user, create_workspace


async def test_dependency_crud_cycle_prevention_risk_and_project_health(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    project = await create_project(client, owner, workspace["id"])
    base = f"/api/v1/workspaces/{workspace['id']}/tasks"
    task_a = await create_task(client, owner, workspace["id"], project["id"], "Task A")
    task_b = await create_task(client, owner, workspace["id"], project["id"], "Task B")
    task_c = await create_task(client, owner, workspace["id"], project["id"], "Task C")

    self_dependency = await client.post(
        f"{base}/{task_a['id']}/dependencies",
        headers=owner["headers"],
        json={"depends_on_task_id": task_a["id"]},
    )
    assert self_dependency.status_code == 409

    first = await client.post(
        f"{base}/{task_a['id']}/dependencies",
        headers=owner["headers"],
        json={"depends_on_task_id": task_b["id"]},
    )
    assert first.status_code == 201, first.text
    second = await client.post(
        f"{base}/{task_b['id']}/dependencies",
        headers=owner["headers"],
        json={"depends_on_task_id": task_c["id"]},
    )
    assert second.status_code == 201
    cycle = await client.post(
        f"{base}/{task_c['id']}/dependencies",
        headers=owner["headers"],
        json={"depends_on_task_id": task_a["id"]},
    )
    assert cycle.status_code == 409
    duplicate = await client.post(
        f"{base}/{task_a['id']}/dependencies",
        headers=owner["headers"],
        json={"depends_on_task_id": task_b["id"]},
    )
    assert duplicate.status_code == 409

    blocked = await client.patch(
        f"{base}/{task_b['id']}", headers=owner["headers"], json={"status": "BLOCKED"}
    )
    assert blocked.status_code == 200
    downstream = await client.get(f"{base}/{task_a['id']}/risk", headers=owner["headers"])
    assert downstream.status_code == 200
    assert downstream.json()["status"] == "AT_RISK"
    assert "Task B" in downstream.json()["reasons"][0]

    health = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/health",
        headers=owner["headers"],
    )
    assert health.status_code == 200
    assert health.json()["health"] == "CRITICAL"
    assert health.json()["blocked_tasks"] == 1

    await client.patch(
        f"{base}/{task_b['id']}",
        headers=owner["headers"],
        json={"status": "TODO", "due_date": date.today().isoformat()},
    )
    at_risk_health = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/health",
        headers=owner["headers"],
    )
    assert at_risk_health.json()["health"] == "AT_RISK"

    listed = await client.get(f"{base}/{task_a['id']}/dependencies", headers=owner["headers"])
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    removed = await client.delete(
        f"{base}/{task_a['id']}/dependencies/{task_b['id']}", headers=owner["headers"]
    )
    assert removed.status_code == 204
    empty = await client.get(f"{base}/{task_a['id']}/dependencies", headers=owner["headers"])
    assert empty.json() == []
