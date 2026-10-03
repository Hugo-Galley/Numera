"""Tests de l'authentification bearer du serveur MCP (sans dépendre de la lib `mcp`).

Lancer : cd mcp-server && python3 -m pytest test_server_auth.py -q
"""
import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

import server_auth

TOKEN = "t" * 32


def _client() -> TestClient:
    app = Starlette(routes=[Route("/sse", lambda request: PlainTextResponse("tools"))])
    return TestClient(server_auth.BearerAuthMiddleware(app, TOKEN))


def test_request_without_token_is_rejected():
    response = _client().get("/sse")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_wrong_token_and_wrong_scheme_are_rejected():
    client = _client()
    assert client.get("/sse", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/sse", headers={"Authorization": f"Basic {TOKEN}"}).status_code == 401


def test_valid_token_is_accepted():
    response = _client().get("/sse", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200
    assert response.text == "tools"


def test_http_transport_refuses_to_start_without_a_strong_token(monkeypatch):
    for value in (None, "", "short"):
        if value is None:
            monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
        else:
            monkeypatch.setenv("MCP_AUTH_TOKEN", value)
        with pytest.raises(SystemExit):
            server_auth.require_auth_token()

    monkeypatch.setenv("MCP_AUTH_TOKEN", TOKEN)
    assert server_auth.require_auth_token() == TOKEN
