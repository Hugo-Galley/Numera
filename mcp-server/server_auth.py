"""Authentification par token bearer pour les transports HTTP du serveur MCP.

Sans cela, n'importe qui pouvant joindre le port MCP utilise les outils (dont écriture et
suppression) avec les identifiants admin du backend. Le transport stdio n'est pas concerné
(le processus est lancé par le client MCP lui-même).
"""
import hmac
import os
import sys

MIN_TOKEN_LENGTH = 16


class BearerAuthMiddleware:
    """Middleware ASGI : refuse (401) toute requête HTTP sans `Authorization: Bearer <token>`."""

    def __init__(self, app, token: str):
        self.app = app
        self._token = token.encode("utf-8")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":  # lifespan, websocket : laissés au serveur
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        authorization = headers.get(b"authorization", b"")
        scheme, _, provided = authorization.partition(b" ")
        if scheme.lower() == b"bearer" and hmac.compare_digest(provided.strip(), self._token):
            await self.app(scope, receive, send)
            return

        body = b'{"detail":"Unauthorized"}'
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"www-authenticate", b"Bearer"),
            ],
        })
        await send({"type": "http.response.body", "body": body})


def require_auth_token() -> str:
    """Retourne MCP_AUTH_TOKEN ou arrête le serveur : pas de transport HTTP sans authentification."""
    token = os.environ.get("MCP_AUTH_TOKEN", "")
    if len(token) < MIN_TOKEN_LENGTH:
        print(
            f"❌ MCP_AUTH_TOKEN (au moins {MIN_TOKEN_LENGTH} caractères) est obligatoire pour les transports "
            "HTTP (sse / streamable-http). Générez-en un : openssl rand -hex 32",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def protect(app):
    """Enveloppe l'application ASGI du serveur MCP avec l'authentification bearer."""
    return BearerAuthMiddleware(app, require_auth_token())
