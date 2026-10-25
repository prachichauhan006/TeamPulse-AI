from app.tests.utils import add_member, create_user, create_workspace

BRIEF = "Messy launch brief: portal release, billing readiness, support training, owners and deadlines."


async def preview(client, user, workspace_id):
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/ai/plans/preview",
        headers=user["headers"],
        json={"brief": BRIEF},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_plan_preview_is_approval_gated_and_reapproval_is_idempotent(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    proposal = await preview(client, owner, workspace["id"])
    assert proposal["status"] == "PENDING"
    assert len(proposal["payload"]["tasks"]) == 4
    assert proposal["result"] is None

    projects_before = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/projects", headers=owner["headers"]
    )
    tasks_before = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/tasks", headers=owner["headers"]
    )
    assert projects_before.json()["total"] == 0
    assert tasks_before.json()["total"] == 0

    approved = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/ai/proposals/{proposal['id']}/approve",
        headers=owner["headers"],
    )
    assert approved.status_code == 200, approved.text
    result = approved.json()["result"]
    assert approved.json()["status"] == "APPROVED"
    assert len(result["task_ids"]) == 4
    assert len(result["dependency_ids"]) == 3

    tasks = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/tasks",
        headers=owner["headers"],
        params={"project_id": result["project_id"], "page_size": 100},
    )
    assert tasks.json()["total"] == 4
    dependencies = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/tasks/{result['task_ids']['task-2']}/dependencies",
        headers=owner["headers"],
    )
    assert len(dependencies.json()) == 1

    replayed = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/ai/proposals/{proposal['id']}/approve",
        headers=owner["headers"],
    )
    assert replayed.status_code == 200
    assert replayed.json()["result"] == result
    projects_after = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/projects", headers=owner["headers"]
    )
    tasks_after = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/tasks", headers=owner["headers"]
    )
    assert projects_after.json()["total"] == 1
    assert tasks_after.json()["total"] == 4

    audit = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/audit-logs", headers=owner["headers"]
    )
    actions = {item["action"] for item in audit.json()["items"]}
    assert {"AI_PLAN_PROPOSAL_CREATED", "AI_PLAN_PROPOSAL_APPROVED"}.issubset(actions)


async def test_rejected_plan_cannot_be_approved_and_creates_no_data(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    proposal = await preview(client, owner, workspace["id"])
    rejected = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/ai/proposals/{proposal['id']}/reject",
        headers=owner["headers"],
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    approval = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/ai/proposals/{proposal['id']}/approve",
        headers=owner["headers"],
    )
    assert approval.status_code == 409
    projects = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/projects", headers=owner["headers"]
    )
    assert projects.json()["total"] == 0


async def test_proposal_access_and_generation_are_workspace_and_role_protected(client):
    owner = await create_user(client, "owner")
    outsider = await create_user(client, "outsider")
    viewer = await create_user(client, "viewer")
    workspace = await create_workspace(client, owner)
    other_workspace = await create_workspace(client, outsider, "Other workspace")
    await add_member(client, owner, workspace["id"], viewer, "VIEWER")
    proposal = await preview(client, owner, workspace["id"])

    forbidden_generation = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/ai/plans/preview",
        headers=viewer["headers"],
        json={"brief": BRIEF},
    )
    assert forbidden_generation.status_code == 403
    foreign_workspace = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/ai/proposals/{proposal['id']}",
        headers=outsider["headers"],
    )
    assert foreign_workspace.status_code == 403
    wrong_workspace_id = await client.get(
        f"/api/v1/workspaces/{other_workspace['id']}/ai/proposals/{proposal['id']}",
        headers=outsider["headers"],
    )
    assert wrong_workspace_id.status_code == 404
    assert proposal["payload"]["project_title"] not in wrong_workspace_id.text
