"""Authentification par token MCP : lecture du token en base et horodatage de sa dernière utilisation."""
import hmac
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.mcp_tokens import hash_token, is_mcp_token
from app.core.time import utcnow_naive
from app.db.system_settings import get_setting
from app.repositories.systeme import admin as admin_repo

LAST_USED_RESOLUTION = timedelta(minutes=1)


def mcp_access_enabled(db: Session) -> bool:
    return bool(get_setting(db, "mcp_enabled", "true").lower() == "true")


def authenticate_mcp_token(db: Session, token: str) -> bool:
    """Vrai si le token correspond à un token actif et que l'accès MCP est activé."""
    if not is_mcp_token(token) or not mcp_access_enabled(db):
        return False
    token_hash = hash_token(token)
    record = admin_repo.mcp_token_by_hash(db, token_hash)
    if record is None or not hmac.compare_digest(record.token_hash, token_hash):
        return False
    now = utcnow_naive()
    if record.last_used_at is None or now - record.last_used_at > LAST_USED_RESOLUTION:
        record.last_used_at = now
        db.commit()
    return True
