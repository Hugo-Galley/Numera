import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core import security

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
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_invalid_username(client: TestClient):
    response = client.post(
        "/auth/token",
        data={"username": "wronguser", "password": "password"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect username or password"
