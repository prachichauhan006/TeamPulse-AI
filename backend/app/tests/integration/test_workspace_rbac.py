from app.tests.utils import add_member, create_project, create_task, create_user, create_workspace


async def test_workspace_roles_and_last_owner_protection(client):
    owner = await create_user(client, "owner")
    admin = await create_user(client, "admin")
    member = await create_user(client, "member")
    viewer = await create_user(client, "viewer")
    workspace = await create_workspace(client, owner)
    workspace_id = workspace["id"]
    await add_member(client, owner, workspace_id, admin, "ADMIN")
    await add_member(client, owner, workspace_id, member, "MEMBER")
    await add_member(client, owner, workspace_id, viewer, "VIEWER")

    project = await create_project(client, owner, workspace_id)
    member_project = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers=member["headers"],
        json={"title": "Member project"},
    )
    assert member_project.status_code == 403

    member_task = await create_task(client, member, workspace_id, project["id"], "Member task")
    assert member_task["title"] == "Member task"
    viewer_task = await client.post(
        f"/api/v1/workspaces/{workspace_id}/tasks",
        headers=viewer["headers"],
        json={"project_id": project["id"], "title": "Viewer task"},
    )
    assert viewer_task.status_code == 403
    viewer_list = await client.get(
        f"/api/v1/workspaces/{workspace_id}/tasks", headers=viewer["headers"]
    )
    assert viewer_list.status_code == 200

    elevated = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=admin["headers"],
        json={"email": viewer["email"], "role": "OWNER"},
    )
    assert elevated.status_code == 403

    demote_owner = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{owner['user']['id']}",
        headers=owner["headers"],
        json={"role": "MEMBER"},
    )
    assert demote_owner.status_code == 409
    remove_owner = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{owner['user']['id']}",
        headers=owner["headers"],
    )
    assert remove_owner.status_code == 409


async def test_workspace_update_delete_confirmation_and_membership_list(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner, "Before rename")
    workspace_id = workspace["id"]

    members = await client.get(f"/api/v1/workspaces/{workspace_id}/members", headers=owner["headers"])
    assert members.status_code == 200
    assert members.json()["total"] == 1
    assert members.json()["items"][0]["role"] == "OWNER"

    updated = await client.patch(
        f"/api/v1/workspaces/{workspace_id}", headers=owner["headers"], json={"name": "After rename"}
    )
    assert updated.status_code == 200
    wrong_confirmation = await client.request(
        "DELETE",
        f"/api/v1/workspaces/{workspace_id}",
        headers=owner["headers"],
        json={"confirmation": "wrong"},
    )
    assert wrong_confirmation.status_code == 422
    deleted = await client.request(
        "DELETE",
        f"/api/v1/workspaces/{workspace_id}",
        headers=owner["headers"],
        json={"confirmation": "After rename"},
    )
    assert deleted.status_code == 204
    inaccessible = await client.get(f"/api/v1/workspaces/{workspace_id}", headers=owner["headers"])
    assert inaccessible.status_code == 403
