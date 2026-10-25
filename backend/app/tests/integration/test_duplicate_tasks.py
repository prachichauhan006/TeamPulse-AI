from app.tests.utils import create_project, create_task, create_user, create_workspace


async def test_duplicate_task_suggestions_use_title_similarity(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    project = await create_project(client, owner, workspace["id"])
    first = await create_task(client, owner, workspace["id"], project["id"], "Prepare launch checklist")
    second = await create_task(client, owner, workspace["id"], project["id"], "Prepare launch checklists")
    await create_task(client, owner, workspace["id"], project["id"], "Reconcile monthly invoice")

    response = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/duplicate-task-suggestions",
        headers=owner["headers"],
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    assert {items[0]["task_id"], items[0]["duplicate_task_id"]} == {first["id"], second["id"]}
    assert items[0]["similarity"] >= 0.72
    assert "similar" in items[0]["reason"]
