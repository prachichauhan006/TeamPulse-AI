from app.tests.utils import create_project, create_task, create_user, create_workspace


async def test_cross_workspace_resources_and_assignees_are_isolated(client):
    owner_a = await create_user(client, "alpha")
    owner_b = await create_user(client, "beta")
    workspace_a = await create_workspace(client, owner_a, "Alpha private")
    workspace_b = await create_workspace(client, owner_b, "Beta private")
    project_a = await create_project(client, owner_a, workspace_a["id"], "Alpha secret project")
    project_b = await create_project(client, owner_b, workspace_b["id"], "Beta project")
    task_a = await create_task(client, owner_a, workspace_a["id"], project_a["id"], "Alpha secret task")

    workspace_response = await client.get(
        f"/api/v1/workspaces/{workspace_a['id']}", headers=owner_b["headers"]
    )
    assert workspace_response.status_code == 403

    project_response = await client.get(
        f"/api/v1/workspaces/{workspace_b['id']}/projects/{project_a['id']}",
        headers=owner_b["headers"],
    )
    assert project_response.status_code == 404
    assert "Alpha" not in project_response.text

    task_response = await client.get(
        f"/api/v1/workspaces/{workspace_b['id']}/tasks/{task_a['id']}",
        headers=owner_b["headers"],
    )
    assert task_response.status_code == 404
    assert "Alpha" not in task_response.text

    invalid_assignee = await client.post(
        f"/api/v1/workspaces/{workspace_b['id']}/tasks",
        headers=owner_b["headers"],
        json={
            "project_id": project_b["id"],
            "title": "Invalid assignment",
            "assignee_id": owner_a["user"]["id"],
        },
    )
    assert invalid_assignee.status_code == 400

    beta_tasks = await client.get(
        f"/api/v1/workspaces/{workspace_b['id']}/tasks", headers=owner_b["headers"]
    )
    assert beta_tasks.status_code == 200
    assert beta_tasks.json()["total"] == 0
    assert "Alpha secret task" not in beta_tasks.text
