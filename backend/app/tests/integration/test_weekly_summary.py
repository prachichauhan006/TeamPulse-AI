from app.tests.utils import create_user, create_workspace


async def test_workspace_weekly_summary_uses_mock_provider(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    response = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/ai/weekly-summary",
        headers=owner["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "ON_TRACK" in body["summary"]
    assert "0 of 0" in body["summary"]
    assert body["recommended_actions"]
