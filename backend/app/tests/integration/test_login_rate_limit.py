from app.tests.utils import TEST_PASSWORD


async def register(client, email: str) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Rate Limit", "password": TEST_PASSWORD},
    )
    assert response.status_code == 201, response.text


async def test_normal_login_works_through_the_allowed_request_limit(client):
    email = "within-limit@example.com"
    await register(client, email)

    for attempt in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": TEST_PASSWORD},
        )
        assert response.status_code == 200, f"Attempt {attempt + 1}: {response.text}"
        assert response.json()["access_token"]


async def test_sixth_login_is_limited_and_untrusted_forwarded_headers_do_not_bypass(client):
    email = "missing-user@example.com"

    # A previous test consumed its own five requests. Autouse fixture reset
    # ensures this test starts with clean state and remains order-independent.
    for attempt in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            headers={"X-Forwarded-For": f"203.0.113.{attempt + 1}"},
            json={"email": email, "password": "WrongPassword123!"},
        )
        assert response.status_code == 401, response.text

    exceeded = await client.post(
        "/api/v1/auth/login",
        headers={"X-Forwarded-For": "203.0.113.250"},
        json={"email": email, "password": "WrongPassword123!"},
    )
    assert exceeded.status_code == 429
    assert exceeded.json() == {"detail": "Too many login attempts. Please try again later."}
    assert 1 <= int(exceeded.headers["retry-after"]) <= 60
    assert "203.0.113" not in exceeded.text
