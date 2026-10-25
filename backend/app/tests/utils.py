import uuid

import httpx

TEST_PASSWORD = "TestPassword123!"


async def create_user(client: httpx.AsyncClient, name: str = "Owner") -> dict:
    email = f"{name.lower()}-{uuid.uuid4().hex[:8]}@example.com"
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": name.title(), "password": TEST_PASSWORD},
    )
    assert register_response.status_code == 201, register_response.text
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD}
    )
    assert login_response.status_code == 200, login_response.text
    tokens = login_response.json()
    return {
        "email": email,
        "user": register_response.json(),
        "tokens": tokens,
        "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
    }


async def create_workspace(client: httpx.AsyncClient, user: dict, name: str = "Core Workspace") -> dict:
    response = await client.post("/api/v1/workspaces", headers=user["headers"], json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def create_project(
    client: httpx.AsyncClient, user: dict, workspace_id: str, title: str = "Launch Project"
) -> dict:
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers=user["headers"],
        json={"title": title, "description": "Integration test project"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_task(
    client: httpx.AsyncClient,
    user: dict,
    workspace_id: str,
    project_id: str,
    title: str,
    **fields,
) -> dict:
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/tasks",
        headers=user["headers"],
        json={"project_id": project_id, "title": title, **fields},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def add_member(
    client: httpx.AsyncClient,
    owner: dict,
    workspace_id: str,
    member: dict,
    role: str,
) -> None:
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner["headers"],
        json={"email": member["email"], "role": role},
    )
    assert response.status_code == 201, response.text
