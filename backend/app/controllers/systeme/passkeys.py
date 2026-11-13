"""Passkeys (WebAuthn) : routes ; la logique est dans `services/systeme/passkeys.py`."""
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_user, get_db, require_interactive_session
from app.schemas.auth import LoginVerifyBody, ReauthBody, RegisterVerifyBody
from app.services.systeme import passkeys as service

router = APIRouter(prefix="/auth/passkey", tags=["auth"])


@router.get("/available")
def passkey_available(db: Session = Depends(get_db)) -> dict[str, bool]:
    return service.passkey_available(db)


@router.get("", dependencies=[Depends(require_interactive_session)])
def list_passkeys(db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> list[dict[str, Any]]:
    return service.list_passkeys(db)


@router.delete("/{credential_id}", dependencies=[Depends(require_interactive_session)])
def delete_passkey(
    credential_id: str,
    body: ReauthBody | None = None,
    db: Session = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict[str, Any]:
    return service.delete_passkey(db, credential_id, body)


@router.post("/register/options", dependencies=[Depends(require_interactive_session)])
def register_options(
    request: Request,
    body: ReauthBody | None = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    return service.register_options(db, request, user, body)


@router.post("/register/verify", dependencies=[Depends(require_interactive_session)])
def register_verify(
    body: RegisterVerifyBody,
    request: Request,
    db: Session = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict[str, Any]:
    return service.register_verify(db, body, request)


@router.post("/login/options")
def login_options(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    return service.login_options(db, request)


@router.post("/login/verify")
def login_verify(body: LoginVerifyBody, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    return service.login_verify(db, body, request)
