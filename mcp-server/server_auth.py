"""Authentification des transports HTTP du serveur MCP par les tokens générés dans Numera.

Le client MCP (Claude Code…) envoie `Authorization: Bearer nmr_…`, token créé dans Paramètres → Sécurité.
Le middleware le fait valider par le backend (`GET /auth/whoami`) avant tout échange MCP : un client
sans token valide ne voit même pas la liste des outils. Le même token est ensuite transmis tel quel au
backend par chaque outil (`server_api.APIClient`) : révocation et interrupteur « Accès MCP » s'appliquent
immédiatement, le serveur MCP ne détient aucun secret.
"""
import hashlib
import json
import time

import httpx

MCP_TOKEN_PREFIX = "nmr_"
# Durée pendant laquelle une validation positive est réutilisée (évite un aller-retour par message MCP)
VALIDATION_CACHE_SECONDS = 30
UNAUTHORIZED_BODY = json.dumps(
    {"detail": "Token MCP invalide ou révoqué. Générez-en un dans Numera : Paramètres → Sécurité."},
    ensure_ascii=False,
).encode("utf-8")


def bearer_token(headers: dict[bytes, bytes]) -> str | None:
    scheme, _, value = headers.get(b"authorization", b"").partition(b" ")
    token = value.strip().decode("latin-1")
    if scheme.lower() != b"bearer" or not token.startswith(MCP_TOKEN_PREFIX):
        return None
    return token


class BackendTokenAuthMiddleware:
    """Middleware ASGI : refuse (401) toute requête HTTP sans token MCP accepté par le backend."""

    def __init__(self, app, api_base_url: str, cache_seconds: float = VALIDATION_CACHE_SECONDS):
        self.app = app
        self._whoami_url = f"{api_base_url.rstrip('/')}/auth/whoami"
        self._cache_seconds = cache_seconds
        self._valid_until: dict[str, float] = {}

    async def _is_valid(self, token: str) -> bool:
        key = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = time.monotonic()
        if self._valid_until.get(key, 0) > now:
            return True
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self._whoami_url, headers={"Authorization": f"Bearer {token}"})
        except httpx.HTTPError:
            return False
        valid = response.status_code == 200 and response.json().get("auth") == "mcp_token"
        if valid:
            self._valid_until[key] = now + self._cache_seconds
        else:
            self._valid_until.pop(key, None)
        return valid

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":  # lifespan : laissé au serveur
            await self.app(scope, receive, send)
            return

        token = bearer_token(dict(scope.get("headers") or []))
        if token and await self._is_valid(token):
            await self.app(scope, receive, send)
            return

        body = UNAUTHORIZED_BODY
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(body)).encode()),
                (b"www-authenticate", b"Bearer"),
            ],
        })
        await send({"type": "http.response.body", "body": body})


def protect(app, api_base_url: str):
    """Enveloppe l'application ASGI du serveur MCP avec la validation des tokens par le backend."""
    return BackendTokenAuthMiddleware(app, api_base_url)
