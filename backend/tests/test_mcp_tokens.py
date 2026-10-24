"""Tokens MCP : création depuis l'interface, accès API, révocation, interrupteur et accès /admin."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.mcp_tokens import hash_token
from app.main import app
from app.models.category import Category
from app.models.mcp_token import McpToken


def _create_token(client: TestClient, name: str = "Claude Code") -> dict:
    response = client.post("/admin/mcp-tokens", json={"name": name, "current_password": "admin"})
    assert response.status_code == 201
    return response.json()


def _as_real_auth():
    """Retire l'override de get_current_user : l'authentification réelle s'applique."""
    app.dependency_overrides.pop(get_current_user, None)


def test_created_token_is_shown_once_and_only_its_hash_is_stored(client: TestClient, db_session: Session):
    created = _create_token(client)
    token = created["token"]
    assert token.startswith("nmr_") and len(token) > 40
    assert created["token_prefix"] == token[:8]

    record = db_session.get(McpToken, created["id"])
    assert record.token_hash == hash_token(token)
    assert token not in (record.token_hash, record.token_prefix)

    listed = client.get("/admin/mcp-tokens").json()
    assert [item["id"] for item in listed] == [created["id"]]
    assert "token" not in listed[0]


def test_token_grants_api_access_and_records_last_use(client: TestClient, db_session: Session):
    token = _create_token(client)["token"]
    _as_real_auth()
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/accounts", headers=headers).status_code == 200
    assert client.get("/auth/whoami", headers=headers).json()["auth"] == "mcp_token"
    db_session.expire_all()
    assert db_session.query(McpToken).one().last_used_at is not None

    assert client.get("/accounts", headers={"Authorization": "Bearer nmr_inconnu"}).status_code == 401
    assert client.get("/auth/whoami").status_code == 401


def test_revoked_token_is_rejected(client: TestClient, db_session: Session):
    created = _create_token(client)
    assert client.delete(f"/admin/mcp-tokens/{created['id']}").status_code == 204
    assert db_session.query(McpToken).count() == 0
    assert client.delete(f"/admin/mcp-tokens/{created['id']}").status_code == 404

    _as_real_auth()
    response = client.get("/accounts", headers={"Authorization": f"Bearer {created['token']}"})
    assert response.status_code == 401


def test_disabling_mcp_access_rejects_every_token(client: TestClient):
    token = _create_token(client)["token"]
    assert client.put("/admin/profile", json={"mcp_enabled": False}).status_code == 200

    _as_real_auth()
    assert client.get("/accounts", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_cannot_reach_admin_routes(client: TestClient):
    token = _create_token(client)["token"]
    _as_real_auth()
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/admin/profile", headers=headers).status_code == 403
    assert client.post("/admin/mcp-tokens", json={"name": "x"}, headers=headers).status_code == 403
    response = client.post(
        "/admin/reset-database", json={"confirm": True, "confirmation_code": "EFFACER"}, headers=headers
    )
    assert response.status_code == 403


def test_token_is_read_only(client: TestClient, db_session: Session):
    token = _create_token(client)["token"]
    _as_real_auth()
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/categories", json={"name": "Créée par un agent", "type": "Sortie"}, headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Accès MCP en lecture seule"
    assert db_session.query(Category).filter(Category.name == "Créée par un agent").count() == 0
    assert client.delete("/transactions/1", headers=headers).status_code == 403
    assert client.patch("/transactions/bulk", json={}, headers=headers).status_code == 403
    assert client.get("/categories", headers=headers).status_code == 200
