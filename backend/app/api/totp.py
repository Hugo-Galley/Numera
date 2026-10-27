"""Double authentification TOTP (Google Authenticator…) exigée après le mot de passe.

La connexion par passkey n'est pas concernée : elle est déjà un facteur fort à elle seule.
Mono-utilisateur : le secret, le dernier pas de temps utilisé (anti-rejeu) et les empreintes des codes
de secours sont stockés dans `system_settings`. Entre le mot de passe et le code, le client détient un
jeton signé à courte durée (`purpose=totp`, sans `sub` : `get_current_user` le refuse).
"""
import json
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_interactive_session
from app.core import security, totp
from app.core.config import settings
from app.core.logging import get_logger
from app.core.login_rate_limit import LoginRateLimiter
from app.db.session import get_db
from app.db.system_settings import get_setting, set_setting

logger = get_logger(__name__)

router = APIRouter(prefix="/auth/totp", tags=["auth"])

SECRET_KEY_SETTING = "totp_secret"
PENDING_KEY_SETTING = "totp_pending_secret"
LAST_STEP_SETTING = "totp_last_step"
RECOVERY_SETTING = "totp_recovery_codes"
MFA_TOKEN_TTL_SECONDS = 300

# Compteur distinct du mot de passe : deviner le code après un mot de passe valide reste borné
totp_rate_limiter = LoginRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_SECONDS,
    lockout_seconds=settings.LOGIN_LOCKOUT_SECONDS,
)


class TotpStatus(BaseModel):
    enabled: bool
    recovery_codes_left: int


class TotpSetupBody(BaseModel):
    current_password: str


class TotpSetup(BaseModel):
    secret: str
    otpauth_uri: str
    qr_svg: str


class CodeBody(BaseModel):
    code: str


class DisableBody(BaseModel):
    current_password: str
    code: str


class RecoveryCodes(BaseModel):
    recovery_codes: list[str]


class TotpLoginBody(BaseModel):
    mfa_token: str
    code: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str


def is_enabled(db: Session) -> bool:
    return bool(get_setting(db, SECRET_KEY_SETTING))


def create_mfa_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"purpose": "totp", "u": username, "iat": now, "exp": now + timedelta(seconds=MFA_TOKEN_TTL_SECONDS)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def _read_mfa_token(db: Session, token: str) -> str:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Étape de connexion expirée, recommencez")
    if payload.get("purpose") != "totp" or not payload.get("u"):
        raise HTTPException(status_code=401, detail="Étape de connexion invalide")
    # Un changement de mot de passe entre les deux étapes invalide l'étape en cours
    if int(payload.get("iat") or 0) < int(get_setting(db, "auth_valid_after", "0") or 0):
        raise HTTPException(status_code=401, detail="Étape de connexion expirée, recommencez")
    return payload["u"]


def _recovery_hashes(db: Session) -> list[str]:
    try:
        data = json.loads(get_setting(db, RECOVERY_SETTING, "[]"))
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


def _new_recovery_codes(db: Session) -> list[str]:
    codes = totp.generate_recovery_codes()
    set_setting(db, RECOVERY_SETTING, json.dumps([totp.hash_recovery_code(c) for c in codes]))
    return codes


def check_second_factor(db: Session, code: str) -> bool:
    """Code TOTP (jamais deux fois le même) ou code de secours (consommé)."""
    secret = get_setting(db, SECRET_KEY_SETTING)
    if not secret:
        return False
    step = totp.verify(secret, code, int(get_setting(db, LAST_STEP_SETTING, "-1") or -1))
    if step is not None:
        set_setting(db, LAST_STEP_SETTING, str(step))
        return True
    if not totp.normalize_recovery_code(code):
        return False
    hashed = totp.hash_recovery_code(code)
    hashes = _recovery_hashes(db)
    if hashed in hashes:
        hashes.remove(hashed)
        set_setting(db, RECOVERY_SETTING, json.dumps(hashes))
        logger.info("Recovery code used, %d left", len(hashes))
        return True
    return False


def _require_current_password(db: Session, password: str) -> None:
    """400 (jamais 401/403 : le client API déconnecte sur ces codes)."""
    current_hash = get_setting(db, "admin_password_hash", settings.ADMIN_PASSWORD_HASH)
    if not security.verify_password(password, current_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")


@router.get("/status", response_model=TotpStatus, dependencies=[Depends(require_interactive_session)])
def totp_status(db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> TotpStatus:
    enabled = is_enabled(db)
    return TotpStatus(enabled=enabled, recovery_codes_left=len(_recovery_hashes(db)) if enabled else 0)


@router.post("/setup", response_model=TotpSetup, dependencies=[Depends(require_interactive_session)])
def totp_setup(body: TotpSetupBody, db: Session = Depends(get_db), user: str = Depends(get_current_user)) -> TotpSetup:
    """Prépare un secret ; il n'est actif qu'après confirmation d'un premier code (`/enable`)."""
    _require_current_password(db, body.current_password)
    if is_enabled(db):
        raise HTTPException(status_code=409, detail="Double authentification déjà activée")
    secret = totp.generate_secret()
    set_setting(db, PENDING_KEY_SETTING, secret)
    uri = totp.provisioning_uri(secret, user)
    return TotpSetup(secret=secret, otpauth_uri=uri, qr_svg=totp.qr_svg_data_uri(uri))


@router.post("/enable", response_model=RecoveryCodes, dependencies=[Depends(require_interactive_session)])
def totp_enable(body: CodeBody, db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> RecoveryCodes:
    pending = get_setting(db, PENDING_KEY_SETTING)
    if not pending:
        raise HTTPException(status_code=400, detail="Aucune configuration en cours")
    step = totp.verify(pending, body.code)
    if step is None:
        raise HTTPException(status_code=400, detail="Code incorrect")
    set_setting(db, SECRET_KEY_SETTING, pending)
    set_setting(db, PENDING_KEY_SETTING, "")
    set_setting(db, LAST_STEP_SETTING, str(step))
    logger.info("TOTP two-factor authentication enabled")
    return RecoveryCodes(recovery_codes=_new_recovery_codes(db))


@router.post("/disable", response_model=TotpStatus, dependencies=[Depends(require_interactive_session)])
def totp_disable(body: DisableBody, db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> TotpStatus:
    """Mot de passe + code exigés : un jeton de session volé ne suffit pas à retirer le second facteur."""
    _require_current_password(db, body.current_password)
    if not is_enabled(db):
        raise HTTPException(status_code=400, detail="Double authentification non activée")
    if not check_second_factor(db, body.code):
        raise HTTPException(status_code=400, detail="Code incorrect")
    for key in (SECRET_KEY_SETTING, PENDING_KEY_SETTING, RECOVERY_SETTING):
        set_setting(db, key, "")
    set_setting(db, LAST_STEP_SETTING, "-1")
    logger.info("TOTP two-factor authentication disabled")
    return TotpStatus(enabled=False, recovery_codes_left=0)


@router.post("/recovery-codes", response_model=RecoveryCodes, dependencies=[Depends(require_interactive_session)])
def regenerate_recovery_codes(body: CodeBody, db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> RecoveryCodes:
    """Remplace tous les codes de secours (les anciens deviennent invalides)."""
    if not is_enabled(db):
        raise HTTPException(status_code=400, detail="Double authentification non activée")
    if not check_second_factor(db, body.code):
        raise HTTPException(status_code=400, detail="Code incorrect")
    return RecoveryCodes(recovery_codes=_new_recovery_codes(db))


@router.post("/login", response_model=AccessToken)
def totp_login(body: TotpLoginBody, request: Request, db: Session = Depends(get_db)) -> AccessToken:
    """Seconde étape de `POST /auth/token` : échange le jeton intermédiaire et le code contre une session."""
    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:totp"
    if not totp_rate_limiter.is_allowed(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(settings.LOGIN_LOCKOUT_SECONDS)},
        )
    username = _read_mfa_token(db, body.mfa_token)
    if username != get_setting(db, "admin_username", settings.ADMIN_USERNAME):
        raise HTTPException(status_code=401, detail="Étape de connexion invalide")
    if not check_second_factor(db, body.code):
        totp_rate_limiter.record_failure(key)
        logger.warning("Failed login attempt: invalid TOTP code")
        raise HTTPException(status_code=401, detail="Code incorrect")
    totp_rate_limiter.reset(key)
    logger.info("Successful login (password + TOTP)")
    token = security.create_access_token(username, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return AccessToken(access_token=token, token_type="bearer")
