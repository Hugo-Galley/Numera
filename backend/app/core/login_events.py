"""Journal des connexions : chaque tentative (réussie ou non) est gardée, dans la limite des plus récentes."""
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.login_event import LoginEvent

logger = get_logger(__name__)

MAX_EVENTS = 200


def client_ip(request: Request) -> str | None:
    """Adresse du client : en production, Nginx la transmet dans X-Real-IP (le backend n'est pas exposé)."""
    forwarded = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "").split(",")[0]
    if forwarded.strip():
        return forwarded.strip()[:64]
    return request.client.host if request.client else None


def record_login(db: Session, request: Request, method: str, success: bool, reason: str | None = None) -> None:
    """Enregistre une tentative. Ne bloque jamais la connexion si l'écriture échoue."""
    # Démo publique : l'IP et le navigateur des visiteurs ne sont ni gardés ni relisibles (RGPD, audit M3)
    keep_identity = not settings.DEMO_MODE
    try:
        db.add(LoginEvent(
            method=method,
            success=success,
            reason=reason,
            ip=client_ip(request) if keep_identity else None,
            user_agent=(request.headers.get("user-agent") or "")[:300] or None if keep_identity else None,
        ))
        db.flush()
        stale = db.query(LoginEvent.id).order_by(LoginEvent.id.desc()).offset(MAX_EVENTS).all()
        if stale:
            db.query(LoginEvent).filter(LoginEvent.id.in_([row.id for row in stale])).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Journal des connexions : écriture impossible")
