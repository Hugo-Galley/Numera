"""Tokens d'accès MCP : générés depuis l'interface, acceptés par l'API à la place d'un JWT.

Le token n'est affiché qu'une fois ; la base ne garde que son empreinte SHA-256 (token aléatoire de
256 bits : un hash lent n'apporte rien). Ils sont refusés quand l'accès MCP est désactivé, ne
permettent que la lecture (GET) et ne donnent pas accès à `/admin` (profil, reset, gestion des tokens).
"""
import hashlib
import secrets

MCP_TOKEN_PREFIX = "nmr_"


def is_mcp_token(token: str | None) -> bool:
    return token is not None and token.startswith(MCP_TOKEN_PREFIX)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    return MCP_TOKEN_PREFIX + secrets.token_urlsafe(32)
