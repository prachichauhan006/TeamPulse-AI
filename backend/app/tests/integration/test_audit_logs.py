from app.tests.utils import add_member, create_project, create_task, create_user, create_workspace


async def test_workspace_actions_create_readable_audit_logs(client):
    owner = await create_user(client, "owner")
    viewer = await create_user(client, "viewer")
    workspace = await create_workspace(client, owner)
    await add_member(client, owner, workspace["id"], viewer, "VIEWER")
    project = await create_project(client, owner, workspace["id"])
    task_a = await create_task(client, owner, workspace["id"], project["id"], "Audit A")
    task_b = await create_task(client, owner, workspace["id"], project["id"], "Audit B")
    dependency = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/tasks/{task_a['id']}/dependencies",
        headers=owner["headers"],
        json={"depends_on_task_id": task_b["id"]},
    )
    assert dependency.status_code == 201

    response = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/audit-logs",
        headers=owner["headers"],
        params={"page_size": 100},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    actions = {item["action"] for item in body["items"]}
    assert {
        "WORKSPACE_CREATED",
        "WORKSPACE_MEMBER_ADDED",
        "PROJECT_CREATED",
        "TASK_CREATED",
        "TASK_DEPENDENCY_ADDED",
    }.issubset(actions)
    assert all(item["workspace_id"] == workspace["id"] for item in body["items"])
    assert all("password" not in item["metadata"] for item in body["items"])

    viewer_response = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/audit-logs", headers=viewer["headers"]
    )
    assert viewer_response.status_code == 403
