from app.tests.utils import create_user, create_workspace


async def create_note(client, user, workspace_id):
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/meeting-notes",
        headers=user["headers"],
        json={"title": "Rate limit notes", "content": "Action: Review the rate-limit behavior"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_ai_limit_allows_ten_then_rejects_and_is_per_user(client):
    first_user = await create_user(client, "first")
    second_user = await create_user(client, "second")
    first_workspace = await create_workspace(client, first_user, "First")
    second_workspace = await create_workspace(client, second_user, "Second")

    for attempt in range(10):
        response = await client.get(
            f"/api/v1/workspaces/{first_workspace['id']}/ai/proposals",
            headers=first_user["headers"],
        )
        assert response.status_code == 200, f"Attempt {attempt + 1}: {response.text}"

    exceeded = await client.get(
        f"/api/v1/workspaces/{first_workspace['id']}/ai/proposals",
        headers=first_user["headers"],
    )
    assert exceeded.status_code == 429
    assert exceeded.json() == {"detail": "Too many requests. Please try again later."}
    assert 1 <= int(exceeded.headers["retry-after"]) <= 60

    other_user = await client.get(
        f"/api/v1/workspaces/{second_workspace['id']}/ai/proposals",
        headers=second_user["headers"],
    )
    assert other_user.status_code == 200


async def test_meeting_ai_extraction_limit_allows_ten_then_rejects(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    note = await create_note(client, owner, workspace["id"])

    for attempt in range(10):
        response = await client.post(
            f"/api/v1/workspaces/{workspace['id']}/meeting-notes/{note['id']}/extract-actions",
            headers=owner["headers"],
        )
        assert response.status_code == 201, f"Attempt {attempt + 1}: {response.text}"

    exceeded = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/meeting-notes/{note['id']}/extract-actions",
        headers=owner["headers"],
    )
    assert exceeded.status_code == 429
    assert 1 <= int(exceeded.headers["retry-after"]) <= 60


async def test_search_limit_allows_thirty_then_rejects(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)

    for attempt in range(30):
        response = await client.get(
            f"/api/v1/workspaces/{workspace['id']}/search",
            headers=owner["headers"],
            params={"q": "rate limit"},
        )
        assert response.status_code == 200, f"Attempt {attempt + 1}: {response.text}"

    exceeded = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/search",
        headers=owner["headers"],
        params={"q": "rate limit"},
    )
    assert exceeded.status_code == 429
    assert exceeded.json() == {"detail": "Too many requests. Please try again later."}
    assert 1 <= int(exceeded.headers["retry-after"]) <= 60
