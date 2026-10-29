"""Connexion par passkey (WebAuthn : Face ID / Touch ID) en complément du mot de passe.

Mono-utilisateur : les passkeys enregistrées sont stockées en JSON dans `system_settings`. Le défi
WebAuthn voyage dans un jeton signé à courte durée (aucun état serveur). L'origine de la requête doit
figurer dans `CORS_ORIGINS` ; l'identifiant de la partie de confiance (RP ID) en est le nom d'hôte.
"""
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
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

from app.core.login_rate_limit import client_key, login_rate_limiter
from app.controllers.deps import get_current_user, require_interactive_session
from app.core import security
from app.core.config import settings
from app.core.logging import get_logger
from app.core.login_events import record_login
from app.db.session import get_db
from app.db.system_settings import get_setting, set_setting

logger = get_logger(__name__)

router = APIRouter(prefix="/auth/passkey", tags=["auth"])

SETTING_KEY = "webauthn_credentials"
CHALLENGE_TTL_SECONDS = 300
RP_NAME = "Numera"


class RegisterVerifyBody(BaseModel):
    state: str
    credential: dict
    name: str | None = None


class LoginVerifyBody(BaseModel):
    state: str
    credential: dict


def _load(db: Session) -> list[dict]:
    raw = get_setting(db, SETTING_KEY, "[]")
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


def _save(db: Session, credentials: list[dict]) -> None:
    set_setting(db, SETTING_KEY, json.dumps(credentials))


def _origin(request: Request) -> tuple[str, str]:
    """Origine du navigateur et RP ID (son nom d'hôte).

    Acceptée si elle figure dans `CORS_ORIGINS` ou si son nom d'hôte est celui par lequel la requête
    est arrivée (en-tête Host / X-Forwarded-Host posé par le reverse proxy) : une passkey fonctionne
    ainsi depuis l'adresse réellement utilisée sans réglage supplémentaire.
    """
    origin = (request.headers.get("origin") or "").rstrip("/")
    host = urlparse(origin).hostname
    if not host:
        raise HTTPException(status_code=400, detail="Origine invalide")
    served = {
        urlparse(f"//{value.split(',')[0].strip()}").hostname
        for value in (request.headers.get("x-forwarded-host"), request.headers.get("host"))
        if value
    }
    if origin not in settings.cors_origins and host not in served:
        raise HTTPException(status_code=400, detail="Origine non autorisée pour les passkeys")
    return origin, host


def _sign_challenge(challenge: bytes, purpose: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(seconds=CHALLENGE_TTL_SECONDS)
    return jwt.encode(
        {"purpose": purpose, "ch": bytes_to_base64url(challenge), "exp": exp},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def _read_challenge(state: str, purpose: str) -> bytes:
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Défi expiré ou invalide")
    if payload.get("purpose") != purpose:
        raise HTTPException(status_code=400, detail="Défi invalide")
    if not payload.get("ch"):
        raise HTTPException(status_code=400, detail="Défi invalide")
    return base64url_to_bytes(payload["ch"])


def _admin_username(db: Session) -> str:
    return get_setting(db, "admin_username", settings.ADMIN_USERNAME)


@router.get("/available")
def passkey_available(db: Session = Depends(get_db)) -> dict[str, bool]:
    return {"available": bool(_load(db))}


@router.get("", dependencies=[Depends(require_interactive_session)])
def list_passkeys(db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> list[dict]:
    return [
        {"id": c["id"], "name": c["name"], "created_at": c["created_at"], "last_used_at": c.get("last_used_at")}
        for c in _load(db)
    ]


@router.delete("/{credential_id}", dependencies=[Depends(require_interactive_session)])
def delete_passkey(credential_id: str, db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> dict:
    credentials = _load(db)
    remaining = [c for c in credentials if c["id"] != credential_id]
    if len(remaining) == len(credentials):
        raise HTTPException(status_code=404, detail="Passkey introuvable")
    _save(db, remaining)
    return {"ok": True}


@router.post("/register/options", dependencies=[Depends(require_interactive_session)])
def register_options(request: Request, db: Session = Depends(get_db), user: str = Depends(get_current_user)) -> dict:
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


@router.post("/register/verify", dependencies=[Depends(require_interactive_session)])
def register_verify(
    body: RegisterVerifyBody,
    request: Request,
    db: Session = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
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
        raise HTTPException(status_code=400, detail="Enregistrement de la passkey refusé")

    credentials = _load(db)
    credential_id = bytes_to_base64url(verified.credential_id)
    if any(c["id"] == credential_id for c in credentials):
        raise HTTPException(status_code=409, detail="Passkey déjà enregistrée")
    credentials.append(
        {
            "id": credential_id,
            "public_key": bytes_to_base64url(verified.credential_public_key),
            "sign_count": verified.sign_count,
            "name": (body.name or "").strip()[:60] or f"Passkey {len(credentials) + 1}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used_at": None,
        }
    )
    _save(db, credentials)
    return {"ok": True, "id": credential_id}


@router.post("/login/options")
def login_options(request: Request, db: Session = Depends(get_db)) -> dict:
    _, rp_id = _origin(request)
    credentials = _load(db)
    if not credentials:
        raise HTTPException(status_code=404, detail="Aucune passkey enregistrée")
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["id"])) for c in credentials],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return {"options": json.loads(options_to_json(options)), "state": _sign_challenge(options.challenge, "login")}


@router.post("/login/verify")
def login_verify(body: LoginVerifyBody, request: Request, db: Session = Depends(get_db)) -> dict:
    key = client_key(request, "passkey")
    if not login_rate_limiter.is_allowed(key):
        record_login(db, request, "passkey", False, "rate_limited")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(settings.LOGIN_LOCKOUT_SECONDS)},
        )
    origin, rp_id = _origin(request)
    challenge = _read_challenge(body.state, "login")

    credentials = _load(db)
    stored = next((c for c in credentials if c["id"] == body.credential.get("id")), None)
    if stored is None:
        login_rate_limiter.record_failure(key)
        record_login(db, request, "passkey", False, "invalid_passkey")
        raise HTTPException(status_code=401, detail="Passkey inconnue")
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
        raise HTTPException(status_code=401, detail="Connexion par passkey refusée")

    stored["sign_count"] = verified.new_sign_count
    stored["last_used_at"] = datetime.now(timezone.utc).isoformat()
    _save(db, credentials)
    login_rate_limiter.reset(key)
    logger.info("Successful passkey login")
    record_login(db, request, "passkey", True)
    token = security.create_access_token(
        _admin_username(db), expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}
