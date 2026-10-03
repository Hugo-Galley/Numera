import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core import security
from app.core.login_rate_limit import LoginRateLimiter

def test_login_success(client: TestClient):
    response = client.post(
        "/auth/token",
        data={"username": settings.ADMIN_USERNAME, "password": "admin"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_password(client: TestClient):
    response = client.post(
        "/auth/token",
        data={"username": settings.ADMIN_USERNAME, "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_invalid_username(client: TestClient):
    response = client.post(
        "/auth/token",
        data={"username": "wronguser", "password": "password"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_is_rate_limited(client: TestClient):
    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        response = client.post(
            "/auth/token",
            data={"username": settings.ADMIN_USERNAME, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    response = client.post(
        "/auth/token",
        data={"username": settings.ADMIN_USERNAME, "password": "wrongpassword"},
    )
    assert response.status_code == 429
    assert response.headers["retry-after"] == str(settings.LOGIN_LOCKOUT_SECONDS)


def test_login_rate_limiter_resets_after_success():
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60, lockout_seconds=60)
    limiter.record_failure("client")
    limiter.reset("client")
    assert limiter.is_allowed("client")


def test_cors_allows_only_configured_origins(client: TestClient):
    allowed = client.options(
        "/auth/token",
        headers={
            "Origin": settings.cors_origins[0],
            "Access-Control-Request-Method": "POST",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == settings.cors_origins[0]

    denied = client.options(
        "/auth/token",
        headers={
            "Origin": "https://attacker.invalid",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in denied.headers


def test_invalid_token_returns_401(client: TestClient):
    from app.main import app
    from app.api.deps import get_current_user
    
    app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.get("/accounts", headers={"Authorization": "Bearer invalid_or_expired_token"})
        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "Bearer" or response.headers.get("WWW-Authenticate") == "Bearer"
    finally:
        app.dependency_overrides[get_current_user] = lambda: "admin"


# ─── Vrai flux JWT (sans override de get_current_user) ──────────────────────

@pytest.fixture()
def real_auth_client(client: TestClient):
    from app.api.deps import get_current_user
    from app.main import app

    app.dependency_overrides.pop(get_current_user, None)
    yield client


def _login(client: TestClient, password: str = "admin") -> str:
    response = client.post("/auth/token", data={"username": settings.ADMIN_USERNAME, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_jwt_round_trip_and_rejection_of_invalid_tokens(real_auth_client: TestClient):
    from datetime import timedelta

    assert real_auth_client.get("/accounts").status_code == 401

    token = _login(real_auth_client)
    ok = real_auth_client.get("/accounts", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200

    forged = security.jwt.encode({"sub": settings.ADMIN_USERNAME}, "another-secret-key-of-32-characters!", algorithm="HS256")
    assert real_auth_client.get("/accounts", headers={"Authorization": f"Bearer {forged}"}).status_code == 401

    expired = security.create_access_token(settings.ADMIN_USERNAME, expires_delta=timedelta(minutes=-1))
    assert real_auth_client.get("/accounts", headers={"Authorization": f"Bearer {expired}"}).status_code == 401

    assert real_auth_client.get("/accounts", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_changing_password_requires_current_password_and_minimum_length(real_auth_client: TestClient):
    headers = {"Authorization": f"Bearer {_login(real_auth_client)}"}

    missing = real_auth_client.put("/admin/profile", json={"password": "newpassword1"}, headers=headers)
    assert missing.status_code == 400

    wrong = real_auth_client.put(
        "/admin/profile", json={"password": "newpassword1", "current_password": "nope"}, headers=headers
    )
    assert wrong.status_code == 400

    too_short = real_auth_client.put(
        "/admin/profile", json={"password": "short", "current_password": "admin"}, headers=headers
    )
    assert too_short.status_code == 422

    # Les anciens identifiants fonctionnent toujours : rien n'a été modifié par les refus
    _login(real_auth_client, "admin")

    ok = real_auth_client.put(
        "/admin/profile", json={"password": "newpassword1", "current_password": "admin"}, headers=headers
    )
    assert ok.status_code == 200
    _login(real_auth_client, "newpassword1")
    assert real_auth_client.post(
        "/auth/token", data={"username": settings.ADMIN_USERNAME, "password": "admin"}
    ).status_code == 401


def test_profile_update_without_credential_change_needs_no_current_password(real_auth_client: TestClient):
    headers = {"Authorization": f"Bearer {_login(real_auth_client)}"}
    response = real_auth_client.put("/admin/profile", json={"mcp_enabled": False}, headers=headers)
    assert response.status_code == 200
    assert response.json()["mcp_enabled"] is False
