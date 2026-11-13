"""Connexion par passkey (WebAuthn : Face ID / Touch ID) en complément du mot de passe.

Mono-utilisateur : les passkeys enregistrées sont stockées en JSON dans `system_settings`. Le défi
WebAuthn voyage dans un jeton signé à courte durée (aucun état serveur). L'origine de la requête doit
figurer dans `CORS_ORIGINS` ; l'identifiant de la partie de confiance (RP ID) en est le nom d'hôte.
"""
import json
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

import jwt
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core import security
from app.core.config import settings
from app.core.errors import AuthenticationError, ConflictError, InvalidOperationError, NotFoundError, RateLimitedError
from app.core.i18n import tr
from app.core.logging import get_logger
from app.core.login_events import record_login
from app.core.login_rate_limit import client_key, login_rate_limiter
from app.core.time import utcnow_aware
from app.db.system_settings import get_setting, set_setting
from app.schemas.auth import LoginVerifyBody, ReauthBody, RegisterVerifyBody
from app.services.systeme import admin as admin_service

logger = get_logger(__name__)

SETTING_KEY = "webauthn_credentials"
CHALLENGE_TTL_SECONDS = 300
RP_NAME = "Numera"


def _load(db: Session) -> list[dict[str, Any]]:
    raw = get_setting(db, SETTING_KEY, "[]")
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


def _save(db: Session, credentials: list[dict[str, Any]]) -> None:
    set_setting(db, SETTING_KEY, json.dumps(credentials))
    db.commit()


def _origin(request: Any) -> tuple[str, str]:
    """Origine du navigateur et RP ID (son nom d'hôte).

    Acceptée si elle figure dans `CORS_ORIGINS` ou si son nom d'hôte est celui par lequel la requête
    est arrivée (en-tête Host / X-Forwarded-Host posé par le reverse proxy) : une passkey fonctionne
    ainsi depuis l'adresse réellement utilisée sans réglage supplémentaire.
    """
    origin = (request.headers.get("origin") or "").rstrip("/")
    host = urlparse(origin).hostname
    if not host:
        raise InvalidOperationError(tr("errors.passkey_origin_invalid"))
    served = {
        urlparse(f"//{value.split(',')[0].strip()}").hostname
        for value in (request.headers.get("x-forwarded-host"), request.headers.get("host"))
        if value
    }
    if origin not in settings.cors_origins and host not in served:
        raise InvalidOperationError(tr("errors.passkey_origin_forbidden"))
    return origin, host


def _sign_challenge(challenge: bytes, purpose: str) -> str:
    exp = utcnow_aware() + timedelta(seconds=CHALLENGE_TTL_SECONDS)
    return jwt.encode(
        {"purpose": purpose, "ch": bytes_to_base64url(challenge), "exp": exp},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def _read_challenge(state: str, purpose: str) -> bytes:
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        raise InvalidOperationError(tr("errors.passkey_challenge_expired")) from None
    if payload.get("purpose") != purpose:
        raise InvalidOperationError(tr("errors.passkey_challenge_invalid"))
    if not payload.get("ch"):
        raise InvalidOperationError(tr("errors.passkey_challenge_invalid"))
    return base64url_to_bytes(payload["ch"])


def _admin_username(db: Session) -> str:
    username: str = get_setting(db, "admin_username", settings.ADMIN_USERNAME)
    return username


def passkey_available(db: Session) -> dict[str, bool]:
    return {"available": bool(_load(db))}


def list_passkeys(db: Session) -> list[dict[str, Any]]:
    return [
        {"id": c["id"], "name": c["name"], "created_at": c["created_at"], "last_used_at": c.get("last_used_at")}
        for c in _load(db)
    ]


def delete_passkey(db: Session, credential_id: str, body: ReauthBody | None = None) -> dict[str, Any]:
    body = body or ReauthBody()
    admin_service.require_reauth(db, body.current_password, body.code)
    credentials = _load(db)
    remaining = [c for c in credentials if c["id"] != credential_id]
    if len(remaining) == len(credentials):
        raise NotFoundError(tr("errors.passkey_not_found"))
    _save(db, remaining)
    return {"ok": True}


def register_options(db: Session, request: Any, user: str, body: ReauthBody | None = None) -> dict[str, Any]:
    # Le code TOTP, à usage unique, n'est exigé qu'à la validation (`register/verify`)
    admin_service.require_current_password(db, (body or ReauthBody()).current_password)
    _, rp_id = _origin(request)
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=RP_NAME,
        user_id=_admin_username(db).encode(),
        user_name=user,
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["id"])) for c in _load(db)],
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    return {"options": json.loads(options_to_json(options)), "state": _sign_challenge(options.challenge, "register")}


def register_verify(db: Session, body: RegisterVerifyBody, request: Any) -> dict[str, Any]:
    admin_service.require_reauth(db, body.current_password, body.code)
    origin, rp_id = _origin(request)
    try:
        verified = verify_registration_response(
            credential=body.credential,
            expected_challenge=_read_challenge(body.state, "register"),
            expected_rp_id=rp_id,
            expected_origin=origin,
            require_user_verification=True,
        )
    except InvalidRegistrationResponse as exc:
        logger.warning("Passkey registration refused: %s", exc)
        raise InvalidOperationError(tr("errors.passkey_register_refused")) from exc

    credentials = _load(db)
    credential_id = bytes_to_base64url(verified.credential_id)
    if any(c["id"] == credential_id for c in credentials):
        raise ConflictError(tr("errors.passkey_exists"))
    credentials.append(
        {
            "id": credential_id,
            "public_key": bytes_to_base64url(verified.credential_public_key),
            "sign_count": verified.sign_count,
            "name": (body.name or "").strip()[:60] or f"Passkey {len(credentials) + 1}",
            "created_at": utcnow_aware().isoformat(),
            "last_used_at": None,
        }
    )
    _save(db, credentials)
    return {"ok": True, "id": credential_id}


def login_options(db: Session, request: Any) -> dict[str, Any]:
    _, rp_id = _origin(request)
    credentials = _load(db)
    if not credentials:
        raise NotFoundError(tr("errors.passkey_none_registered"))
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["id"])) for c in credentials],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return {"options": json.loads(options_to_json(options)), "state": _sign_challenge(options.challenge, "login")}


def login_verify(db: Session, body: LoginVerifyBody, request: Any) -> dict[str, Any]:
    key = client_key(request, "passkey")
    if not login_rate_limiter.is_allowed(key):
        record_login(db, request, "passkey", False, "rate_limited")
        raise RateLimitedError(tr("errors.too_many_attempts"), settings.LOGIN_LOCKOUT_SECONDS)
    origin, rp_id = _origin(request)
    challenge = _read_challenge(body.state, "login")

    credentials = _load(db)
    stored = next((c for c in credentials if c["id"] == body.credential.get("id")), None)
    if stored is None:
        login_rate_limiter.record_failure(key)
        record_login(db, request, "passkey", False, "invalid_passkey")
        raise AuthenticationError(tr("errors.passkey_unknown"))
    try:
        verified = verify_authentication_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=base64url_to_bytes(stored["public_key"]),
            credential_current_sign_count=stored["sign_count"],
            require_user_verification=True,
        )
    except InvalidAuthenticationResponse as exc:
        login_rate_limiter.record_failure(key)
        logger.warning("Passkey login refused: %s", exc)
        record_login(db, request, "passkey", False, "invalid_passkey")
        raise AuthenticationError(tr("errors.passkey_login_refused")) from exc

    stored["sign_count"] = verified.new_sign_count
    stored["last_used_at"] = utcnow_aware().isoformat()
    _save(db, credentials)
    login_rate_limiter.reset(key)
    logger.info("Successful passkey login")
    record_login(db, request, "passkey", True)
    token = security.create_access_token(
        _admin_username(db), expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}
