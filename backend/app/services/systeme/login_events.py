"""Journal des connexions : chaque tentative (réussie ou non) est gardée, dans la limite des plus récentes."""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.request_info import RequestInfo, client_ip
from app.models.login_event import LoginEvent
from app.repositories.systeme import admin as admin_repo

logger = get_logger(__name__)

MAX_EVENTS = 200


def record_login(db: Session, request: RequestInfo, method: str, success: bool, reason: str | None = None) -> None:
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
        admin_repo.prune_login_events(db, MAX_EVENTS)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Journal des connexions : écriture impossible")
