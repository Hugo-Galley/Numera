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
