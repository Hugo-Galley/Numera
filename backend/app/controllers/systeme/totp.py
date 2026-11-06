"""Double authentification TOTP : routes ; la logique est dans `services/systeme/totp.py`."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_user, require_interactive_session
from app.db.session import get_db
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
from app.services.systeme import totp as service

router = APIRouter(prefix="/auth/totp", tags=["auth"])


@router.get("/status", response_model=TotpStatus, dependencies=[Depends(require_interactive_session)])
def totp_status(db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> TotpStatus:
    return service.status(db)


@router.post("/setup", response_model=TotpSetup, dependencies=[Depends(require_interactive_session)])
def totp_setup(body: TotpSetupBody, db: Session = Depends(get_db), user: str = Depends(get_current_user)) -> TotpSetup:
    """Prépare un secret ; il n'est actif qu'après confirmation d'un premier code (`/enable`)."""
    return service.setup(db, body, user)


@router.post("/enable", response_model=RecoveryCodes, dependencies=[Depends(require_interactive_session)])
def totp_enable(body: CodeBody, db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> RecoveryCodes:
    return service.enable(db, body)


@router.post("/disable", response_model=TotpStatus, dependencies=[Depends(require_interactive_session)])
def totp_disable(body: DisableBody, db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> TotpStatus:
    """Mot de passe + code exigés : un jeton de session volé ne suffit pas à retirer le second facteur."""
    return service.disable(db, body)


@router.post("/recovery-codes", response_model=RecoveryCodes, dependencies=[Depends(require_interactive_session)])
def regenerate_recovery_codes(body: CodeBody, db: Session = Depends(get_db), _user: str = Depends(get_current_user)) -> RecoveryCodes:
    """Remplace tous les codes de secours (les anciens deviennent invalides)."""
    return service.regenerate_recovery_codes(db, body)


@router.post("/login", response_model=AccessToken)
def totp_login(body: TotpLoginBody, request: Request, db: Session = Depends(get_db)) -> AccessToken:
    """Seconde étape de `POST /auth/token` : échange le jeton intermédiaire et le code contre une session."""
    return service.login(db, body, request)
