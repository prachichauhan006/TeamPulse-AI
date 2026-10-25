from datetime import date, timedelta

from app.tests.utils import create_project, create_task, create_user, create_workspace


async def test_project_and_task_crud_filtering_and_soft_delete(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    workspace_id = workspace["id"]
    project = await create_project(client, owner, workspace_id, "Release Readiness")

    updated_project = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}",
        headers=owner["headers"],
        json={"status": "ON_HOLD", "description": "Waiting for release approval"},
    )
    assert updated_project.status_code == 200
    assert updated_project.json()["status"] == "ON_HOLD"

    task = await create_task(
        client,
        owner,
        workspace_id,
        project["id"],
        "Prepare deployment checklist",
        assignee_id=owner["user"]["id"],
        due_date=(date.today() + timedelta(days=3)).isoformat(),
        priority="HIGH",
    )
    assert task["assignee_id"] == owner["user"]["id"]
    assert task["version"] == 1

    updated_task = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/tasks/{task['id']}",
        headers=owner["headers"],
        json={"status": "IN_PROGRESS", "priority": "CRITICAL"},
    )
    assert updated_task.status_code == 200
    assert updated_task.json()["status"] == "IN_PROGRESS"
    assert updated_task.json()["version"] == 2

    filtered = await client.get(
        f"/api/v1/workspaces/{workspace_id}/tasks",
        headers=owner["headers"],
        params={"status": "IN_PROGRESS", "q": "deployment", "page": 1, "page_size": 10},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1

    risky_delete = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}", headers=owner["headers"]
    )
    assert risky_delete.status_code == 409
    deleted_task = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/tasks/{task['id']}", headers=owner["headers"]
    )
    assert deleted_task.status_code == 204
    missing_task = await client.get(
        f"/api/v1/workspaces/{workspace_id}/tasks/{task['id']}", headers=owner["headers"]
    )
    assert missing_task.status_code == 404
    deleted_project = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/projects/{project['id']}", headers=owner["headers"]
    )
    assert deleted_project.status_code == 204


async def test_task_rejects_project_from_another_workspace(client):
    owner = await create_user(client, "owner")
    first = await create_workspace(client, owner, "First")
    second = await create_workspace(client, owner, "Second")
    second_project = await create_project(client, owner, second["id"], "Second project")
    response = await client.post(
        f"/api/v1/workspaces/{first['id']}/tasks",
        headers=owner["headers"],
        json={"project_id": second_project["id"], "title": "Cross-tenant task"},
    )
    assert response.status_code == 400
