"""Tests de l'authentification des transports HTTP du serveur MCP (sans dépendre de la lib `mcp`).

Le backend est simulé : `/auth/whoami` accepte uniquement VALID_TOKEN.
Lancer : cd mcp-server && python3 -m pytest test_server_auth.py -q
"""
import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

import server_auth

VALID_TOKEN = "nmr_" + "v" * 43
API_URL = "http://backend:8001"


@pytest.fixture()
def backend_calls(monkeypatch):
    calls: list[str] = []

    def whoami(request: httpx.Request) -> httpx.Response:
        calls.append(request.headers.get("authorization", ""))
        if request.url.path == "/auth/whoami" and request.headers.get("authorization") == f"Bearer {VALID_TOKEN}":
            return httpx.Response(200, json={"username": "admin", "auth": "mcp_token"})
        return httpx.Response(401, json={"detail": "Could not validate credentials"})

    transport = httpx.MockTransport(whoami)
    original = httpx.AsyncClient

    monkeypatch.setattr(server_auth.httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs))
    return calls


def _client() -> TestClient:
    app = Starlette(routes=[Route("/mcp", lambda request: PlainTextResponse("tools"), methods=["POST"])])
    return TestClient(server_auth.protect(app, API_URL))


def test_request_without_token_is_rejected_without_calling_backend(backend_calls):
    response = _client().post("/mcp")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert "Paramètres" in response.json()["detail"]
    assert backend_calls == []


def test_unknown_token_and_wrong_scheme_are_rejected(backend_calls):
    client = _client()
    assert client.post("/mcp", headers={"Authorization": "Bearer nmr_revoque"}).status_code == 401
    assert client.post("/mcp", headers={"Authorization": f"Basic {VALID_TOKEN}"}).status_code == 401
    # Un JWT de session n'est pas un token MCP : refusé sans même interroger le backend
    assert client.post("/mcp", headers={"Authorization": "Bearer eyJhbGciOi.jwt"}).status_code == 401
    assert backend_calls == ["Bearer nmr_revoque"]


def test_valid_token_is_accepted_and_validation_is_cached(backend_calls):
    client = _client()
    for _ in range(3):
        response = client.post("/mcp", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
        assert response.status_code == 200
        assert response.text == "tools"
    assert backend_calls == [f"Bearer {VALID_TOKEN}"]
