"""Tokens d'accès MCP : générés depuis l'interface, acceptés par l'API à la place d'un JWT.

Le token n'est affiché qu'une fois ; la base ne garde que son empreinte SHA-256 (token aléatoire de
256 bits : un hash lent n'apporte rien). Ils sont refusés quand l'accès MCP est désactivé et ne
donnent pas accès à `/admin` (profil, reset, gestion des tokens).
"""
import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.time import utcnow_naive
from app.db.system_settings import get_setting
from app.models.mcp_token import McpToken

MCP_TOKEN_PREFIX = "nmr_"
LAST_USED_RESOLUTION = timedelta(minutes=1)


def is_mcp_token(token: str | None) -> bool:
    return bool(token) and token.startswith(MCP_TOKEN_PREFIX)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    return MCP_TOKEN_PREFIX + secrets.token_urlsafe(32)


def mcp_access_enabled(db: Session) -> bool:
    return get_setting(db, "mcp_enabled", "true").lower() == "true"


def authenticate_mcp_token(db: Session, token: str) -> bool:
    """Vrai si le token correspond à un token actif et que l'accès MCP est activé."""
    if not is_mcp_token(token) or not mcp_access_enabled(db):
        return False
    token_hash = hash_token(token)
    record = db.query(McpToken).filter(McpToken.token_hash == token_hash).first()
    if record is None or not hmac.compare_digest(record.token_hash, token_hash):
        return False
    now = utcnow_naive()
    if record.last_used_at is None or now - record.last_used_at > LAST_USED_RESOLUTION:
        record.last_used_at = now
        db.commit()
    return True
