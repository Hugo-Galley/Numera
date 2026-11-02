"""Test de bout en bout du transport HTTP du serveur MCP (mode API) : un appel d'outil MCP réel.

Le backend est simulé. Vérifie que le token Bearer du client, validé par le middleware, est bien
celui transmis à l'API par l'outil, requête après requête (sans fuite d'un client à l'autre).
Lancer : cd mcp-server && uv run --with pytest python -m pytest test_server_api_http.py -q
"""
import os

os.environ["MCP_TRANSPORT"] = "streamable-http"
os.environ["MCP_API_URL"] = "http://backend:8001"

import httpx
import pytest
from starlette.testclient import TestClient

import server_api
import server_auth

TOKEN_A = "nmr_" + "a" * 43
TOKEN_B = "nmr_" + "b" * 43
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.fixture()
def api_tokens(monkeypatch):
    """Simule le backend ; renvoie la liste des tokens reçus par GET /accounts."""
    received: list[str] = []

    def backend(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("authorization", "")
        if request.url.path == "/auth/whoami":
            ok = auth in (f"Bearer {TOKEN_A}", f"Bearer {TOKEN_B}")
            return httpx.Response(200 if ok else 401, json={"auth": "mcp_token"})
        received.append(auth)
        return httpx.Response(200, json=[{"id": 1, "name": "Courant", "type": "courant", "currency": "EUR"}])

    transport = httpx.MockTransport(backend)
    original = httpx.AsyncClient
    monkeypatch.setattr(server_auth.httpx, "AsyncClient", lambda **kw: original(transport=transport, **kw))
    monkeypatch.setattr(server_api.api, "_client", httpx.Client(transport=transport))
    return received


def _call_list_accounts(client: TestClient, token: str) -> httpx.Response:
    return client.post(
        "/mcp",
        headers={**MCP_HEADERS, "Authorization": f"Bearer {token}"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_accounts", "arguments": {}}},
    )


def test_tool_call_forwards_each_clients_own_token_to_the_api(api_tokens):
    with TestClient(server_auth.protect(server_api.http_app(), server_api.API_BASE_URL)) as client:
        for token in (TOKEN_A, TOKEN_B, TOKEN_A):
            response = _call_list_accounts(client, token)
            assert response.status_code == 200
            assert "Courant" in response.text
    assert api_tokens == [f"Bearer {TOKEN_A}", f"Bearer {TOKEN_B}", f"Bearer {TOKEN_A}"]
