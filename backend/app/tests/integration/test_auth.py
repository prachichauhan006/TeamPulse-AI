from app.tests.utils import TEST_PASSWORD, create_user


async def test_register_login_refresh_rotation_logout_and_me(client):
    user = await create_user(client, "auth")
    me = await client.get("/api/v1/auth/me", headers=user["headers"])
    assert me.status_code == 200
    assert me.json()["email"] == user["email"]

    old_refresh = user["tokens"]["refresh_token"]
    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200, refreshed.text
    rotated = refreshed.json()
    assert rotated["refresh_token"] != old_refresh
    assert rotated["access_token"] != user["tokens"]["access_token"]

    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401

    logged_out = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": rotated["refresh_token"]}
    )
    assert logged_out.status_code == 204
    after_logout = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
    )
    assert after_logout.status_code == 401


async def test_duplicate_registration_and_invalid_login_are_safe(client):
    user = await create_user(client, "duplicate")
    duplicate = await client.post(
        "/api/v1/auth/register",
        json={"email": user["email"], "full_name": "Duplicate", "password": TEST_PASSWORD},
    )
    assert duplicate.status_code == 409
    wrong_login = await client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": "WrongPassword123!"}
    )
    assert wrong_login.status_code == 401
    assert wrong_login.json()["detail"] == "Invalid email or password"


async def test_weak_password_and_invalid_bearer_token_are_rejected(client):
    weak = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "full_name": "Weak", "password": "short"},
    )
    assert weak.status_code == 422
    me = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
    assert me.status_code == 401


async def test_health_endpoint_and_security_headers(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
