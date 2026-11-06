"""Connexion par mot de passe et renouvellement de session."""
import time
from datetime import timedelta
from typing import Any

import jwt
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.errors import AuthenticationError, RateLimitedError
from app.core.i18n import tr
from app.core.logging import get_logger
from app.core.login_events import record_login
from app.core.login_rate_limit import client_key, login_rate_limiter
from app.core.mcp_tokens import is_mcp_token
from app.core.totp import create_mfa_token
from app.core.totp import is_enabled as totp_enabled
from app.db.system_settings import get_setting

logger = get_logger(__name__)


def login(db: Session, request: Any, username: str, password: str) -> dict[str, Any]:
    """Jeton d'accès, ou jeton d'étape (`mfa_required`) quand la double authentification est active."""
    key = client_key(request, username)
    if not login_rate_limiter.is_allowed(key):
        logger.warning("Login temporarily blocked due to repeated failed attempts")
        record_login(db, request, "password", False, "rate_limited")
        raise RateLimitedError(tr("errors.too_many_attempts"), settings.LOGIN_LOCKOUT_SECONDS)

    # Try to get admin credentials from database
    db_username = get_setting(db, "admin_username", settings.ADMIN_USERNAME)
    db_password_hash = get_setting(db, "admin_password_hash", settings.ADMIN_PASSWORD_HASH)

    username_valid = (username == db_username)
    # Dummy bcrypt hash to make verification time constant and prevent timing attacks
    dummy_hash = "$2b$12$e8k8W8eD.2eC/W3W2c/UGeFm3XWzM8/8G6hWj.e4R2q3Z0r4c8h2W"
    hash_to_verify = db_password_hash if username_valid else dummy_hash
    password_valid = security.verify_password(password, hash_to_verify)

    if not username_valid or not password_valid:
        login_rate_limiter.record_failure(key)
        logger.warning("Failed login attempt: invalid credentials")
        record_login(db, request, "password", False, "invalid_password")
        raise AuthenticationError(tr("errors.bad_credentials"), www_authenticate=True)

    login_rate_limiter.reset(key)
    # Double authentification active : pas encore de session, seulement un jeton pour l'étape du code
    if totp_enabled(db):
        logger.info("Password accepted, TOTP code required")
        return {"mfa_required": True, "mfa_token": create_mfa_token(username), "token_type": "mfa"}
    logger.info("Successful login")
    record_login(db, request, "password", True)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(username, expires_delta=access_token_expires),
        "token_type": "bearer",
    }


def whoami(username: str, token: str | None) -> dict[str, str]:
    return {"username": username, "auth": "mcp_token" if is_mcp_token(token) else "session"}


def refresh_access_token(username: str, token: str | None) -> dict[str, Any]:
    """Renouvelle un jeton de session encore valide (l'interface l'appelle quand il expire bientôt).

    La durée d'inactivité reste bornée par l'expiration du jeton ; la durée totale de la session l'est
    par `SESSION_MAX_HOURS` depuis la connexion par mot de passe (`auth_time`). Jamais pour un jeton MCP.
    """
    if token is None:
        raise AuthenticationError(tr("errors.session_expired"), www_authenticate=True)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    # Sans auth_time, la durée totale de la session ne serait pas bornée : pas de renouvellement
    if not payload.get("auth_time"):
        raise AuthenticationError(tr("errors.session_expired"), www_authenticate=True)
    auth_time = int(payload["auth_time"])
    if time.time() - auth_time > settings.SESSION_MAX_HOURS * 3600:
        raise AuthenticationError(tr("errors.session_expired"), www_authenticate=True)
    return {
        "access_token": security.create_access_token(username, auth_time=auth_time),
        "token_type": "bearer",
    }
