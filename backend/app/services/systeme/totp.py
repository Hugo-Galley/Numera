"""Double authentification TOTP (Google Authenticator…) exigée après le mot de passe.

La connexion par passkey n'est pas concernée : elle est déjà un facteur fort à elle seule.
Mono-utilisateur : le secret, le dernier pas de temps utilisé (anti-rejeu) et les empreintes des codes
de secours sont stockés dans `system_settings`. Entre le mot de passe et le code, le client détient un
jeton signé à courte durée (`purpose=totp`, sans `sub` : `get_current_user` le refuse).
"""
import json
from datetime import timedelta
from typing import Any

import jwt
from sqlalchemy.orm import Session

from app.core import security, totp
from app.core.config import settings
from app.core.errors import AuthenticationError, ConflictError, InvalidOperationError, RateLimitedError
from app.core.logging import get_logger
from app.core.login_events import record_login
from app.core.login_rate_limit import totp_rate_limiter
from app.core.totp import LAST_STEP_SETTING, RECOVERY_SETTING, SECRET_KEY_SETTING, check_second_factor, is_enabled, recovery_hashes
from app.db.system_settings import get_setting, set_setting
from app.schemas.auth import (
    AccessToken,
    CodeBody,
    DisableBody,
    RecoveryCodes,
    TotpLoginBody,
    TotpSetup,
    TotpSetupBody,
    TotpStatus,
)

logger = get_logger(__name__)

PENDING_KEY_SETTING = "totp_pending_secret"


def _read_mfa_token(db: Session, token: str) -> str:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        raise AuthenticationError("Étape de connexion expirée, recommencez") from None
    if payload.get("purpose") != "totp" or not payload.get("u"):
        raise AuthenticationError("Étape de connexion invalide")
    # Un changement de mot de passe entre les deux étapes invalide l'étape en cours
    if int(payload.get("iat") or 0) < int(get_setting(db, "auth_valid_after", "0") or 0):
        raise AuthenticationError("Étape de connexion expirée, recommencez")
    return payload["u"]


def _new_recovery_codes(db: Session) -> list[str]:
    codes = totp.generate_recovery_codes()
    set_setting(db, RECOVERY_SETTING, json.dumps([totp.hash_recovery_code(c) for c in codes]))
    return codes


def _require_current_password(db: Session, password: str) -> None:
    """400 (jamais 401/403 : le client API déconnecte sur ces codes)."""
    current_hash = get_setting(db, "admin_password_hash", settings.ADMIN_PASSWORD_HASH)
    if not security.verify_password(password, current_hash):
        raise InvalidOperationError("Mot de passe actuel incorrect")


def status(db: Session) -> TotpStatus:
    enabled = is_enabled(db)
    return TotpStatus(enabled=enabled, recovery_codes_left=len(recovery_hashes(db)) if enabled else 0)


def setup(db: Session, body: TotpSetupBody, user: str) -> TotpSetup:
    """Prépare un secret ; il n'est actif qu'après confirmation d'un premier code (`enable`)."""
    _require_current_password(db, body.current_password)
    if is_enabled(db):
        raise ConflictError("Double authentification déjà activée")
    secret = totp.generate_secret()
    set_setting(db, PENDING_KEY_SETTING, secret)
    db.commit()
    uri = totp.provisioning_uri(secret, user)
    return TotpSetup(secret=secret, otpauth_uri=uri, qr_svg=totp.qr_svg_data_uri(uri))


def enable(db: Session, body: CodeBody) -> RecoveryCodes:
    pending = get_setting(db, PENDING_KEY_SETTING)
    if not pending:
        raise InvalidOperationError("Aucune configuration en cours")
    step = totp.verify(pending, body.code)
    if step is None:
        raise InvalidOperationError("Code incorrect")
    set_setting(db, SECRET_KEY_SETTING, pending)
    set_setting(db, PENDING_KEY_SETTING, "")
    set_setting(db, LAST_STEP_SETTING, str(step))
    codes = _new_recovery_codes(db)
    db.commit()  # secret, étape et codes de secours ensemble : jamais de 2FA active sans codes
    logger.info("TOTP two-factor authentication enabled")
    return RecoveryCodes(recovery_codes=codes)


def disable(db: Session, body: DisableBody) -> TotpStatus:
    """Mot de passe + code exigés : un jeton de session volé ne suffit pas à retirer le second facteur."""
    _require_current_password(db, body.current_password)
    if not is_enabled(db):
        raise InvalidOperationError("Double authentification non activée")
    if not check_second_factor(db, body.code):
        raise InvalidOperationError("Code incorrect")
    for key in (SECRET_KEY_SETTING, PENDING_KEY_SETTING, RECOVERY_SETTING):
        set_setting(db, key, "")
    set_setting(db, LAST_STEP_SETTING, "-1")
    db.commit()
    logger.info("TOTP two-factor authentication disabled")
    return TotpStatus(enabled=False, recovery_codes_left=0)


def regenerate_recovery_codes(db: Session, body: CodeBody) -> RecoveryCodes:
    """Remplace tous les codes de secours (les anciens deviennent invalides)."""
    if not is_enabled(db):
        raise InvalidOperationError("Double authentification non activée")
    if not check_second_factor(db, body.code):
        raise InvalidOperationError("Code incorrect")
    codes = _new_recovery_codes(db)
    db.commit()
    return RecoveryCodes(recovery_codes=codes)


def login(db: Session, body: TotpLoginBody, request: Any) -> AccessToken:
    """Seconde étape de la connexion : échange le jeton intermédiaire et le code contre une session."""
    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:totp"
    if not totp_rate_limiter.is_allowed(key):
        record_login(db, request, "password_totp", False, "rate_limited")
        raise RateLimitedError("Too many login attempts. Try again later.", settings.LOGIN_LOCKOUT_SECONDS)
    username = _read_mfa_token(db, body.mfa_token)
    if username != get_setting(db, "admin_username", settings.ADMIN_USERNAME):
        raise AuthenticationError("Étape de connexion invalide")
    if not check_second_factor(db, body.code):
        totp_rate_limiter.record_failure(key)
        logger.warning("Failed login attempt: invalid TOTP code")
        record_login(db, request, "password_totp", False, "invalid_totp")
        raise AuthenticationError("Code incorrect")
    db.commit()  # pas de rejeu : l'étape TOTP consommée est enregistrée
    totp_rate_limiter.reset(key)
    logger.info("Successful login (password + TOTP)")
    record_login(db, request, "password_totp", True)
    token = security.create_access_token(username, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return AccessToken(access_token=token, token_type="bearer")
