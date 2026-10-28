"""Audit R8, R9, R10 : documentation fermée en prod, JWT strict, limiteur de connexion borné."""
import time
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.controllers.deps import get_current_user
from app.core import login_rate_limit, security
from app.core.config import settings
from app.core.login_rate_limit import LoginRateLimiter
from app.main import app, docs_kwargs


@pytest.fixture()
def real_auth_client(client: TestClient):
    app.dependency_overrides.pop(get_current_user, None)
    yield client


def _login(client, password="admin") -> str:
    r = client.post("/auth/token", data={"username": settings.ADMIN_USERNAME, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- R8 ----------------------------------------------------------------------------------

def test_api_documentation_is_disabled_in_production():
    assert docs_kwargs("prod") == {"docs_url": None, "redoc_url": None, "openapi_url": None}
    assert docs_kwargs("dev") == {}


# --- R9 ----------------------------------------------------------------------------------

def test_token_without_exp_is_rejected(real_auth_client):
    token = jwt.encode({"sub": settings.ADMIN_USERNAME}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert real_auth_client.get("/accounts", headers=_headers(token)).status_code == 401


def test_refresh_requires_auth_time(real_auth_client):
    token = security.create_access_token(settings.ADMIN_USERNAME)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    payload.pop("auth_time")
    stripped = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert real_auth_client.post("/auth/refresh", headers=_headers(stripped)).status_code == 401


def test_changing_the_password_invalidates_existing_sessions(real_auth_client, monkeypatch):
    old_token = _login(real_auth_client)
    assert real_auth_client.get("/accounts", headers=_headers(old_token)).status_code == 200

    time.sleep(1.1)  # auth_time a la précision de la seconde
    r = real_auth_client.put(
        "/admin/profile",
        json={"password": "nouveau-mot-de-passe", "current_password": "admin"},
        headers=_headers(old_token),
    )
    assert r.status_code == 200, r.text
    assert real_auth_client.get("/accounts", headers=_headers(old_token)).status_code == 401

    new_token = _login(real_auth_client, "nouveau-mot-de-passe")
    assert real_auth_client.get("/accounts", headers=_headers(new_token)).status_code == 200


# --- R10 ---------------------------------------------------------------------------------

def test_rate_limiter_forgets_expired_entries(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(login_rate_limit, "monotonic", lambda: clock["now"])
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=60, lockout_seconds=60)

    for i in range(200):  # 200 identifiants différents, chacun un seul échec
        limiter.record_failure(f"1.2.3.4:user{i}")
    clock["now"] += 3600
    limiter.record_failure("1.2.3.4:autre")  # déclenche le ménage

    assert len(limiter._attempts) <= 2
    assert len(limiter._locked_until) == 0
