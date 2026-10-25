from app.tests.utils import create_project, create_user, create_workspace

NOTES = "Weekly launch sync\nDecision: Launch on Friday\nAction: Prepare release notes\nAction: Verify deployment checklist"


async def test_meeting_extraction_preview_and_selected_action_approval(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    project = await create_project(client, owner, workspace["id"])
    created = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/meeting-notes",
        headers=owner["headers"],
        json={"title": "Launch sync", "content": NOTES, "project_id": project["id"]},
    )
    assert created.status_code == 201, created.text
    note = created.json()
    assert note["embedding_status"] == "COMPLETE"

    listed = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/meeting-notes", headers=owner["headers"]
    )
    assert listed.json()["total"] == 1
    read = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/meeting-notes/{note['id']}", headers=owner["headers"]
    )
    assert read.json()["content"] == NOTES

    extracted = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/meeting-notes/{note['id']}/extract-actions",
        headers=owner["headers"],
    )
    assert extracted.status_code == 201, extracted.text
    proposal = extracted.json()
    assert proposal["status"] == "PENDING"
    assert len(proposal["payload"]["action_items"]) == 2
    assert proposal["payload"]["decisions"] == ["Launch on Friday"]
    tasks_before = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/tasks", headers=owner["headers"]
    )
    assert tasks_before.json()["total"] == 0

    approval_payload = {"proposal_id": proposal["id"], "action_item_keys": ["action-2"]}
    approved = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/meeting-notes/{note['id']}/approve-actions",
        headers=owner["headers"],
        json=approval_payload,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["result"]["selected_action_item_keys"] == ["action-2"]
    tasks = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/tasks", headers=owner["headers"]
    )
    assert tasks.json()["total"] == 1
    assert tasks.json()["items"][0]["title"] == "Verify deployment checklist"

    replayed = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/meeting-notes/{note['id']}/approve-actions",
        headers=owner["headers"],
        json=approval_payload,
    )
    assert replayed.status_code == 200
    assert replayed.json()["result"] == approved.json()["result"]
    tasks_after = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/tasks", headers=owner["headers"]
    )
    assert tasks_after.json()["total"] == 1

    audit = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/audit-logs", headers=owner["headers"]
    )
    actions = {item["action"] for item in audit.json()["items"]}
    assert {"MEETING_NOTE_CREATED", "MEETING_ACTIONS_EXTRACTED", "MEETING_ACTIONS_APPROVED"}.issubset(actions)
