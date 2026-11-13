"""Connexion et session : routes ; la logique est dans `services/systeme/auth.py`."""
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_user, get_db, optional_oauth2, require_interactive_session
from app.services.systeme import auth as service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
def login_access_token(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests"""
    return service.login(db, request, form_data.username, form_data.password)


@router.get("/whoami")
def whoami(
    username: str = Depends(get_current_user),
    token: str | None = Depends(optional_oauth2),
) -> dict[str, str]:
    """Valide les identifiants présentés (utilisé par le serveur MCP pour filtrer les clients)."""
    return service.whoami(username, token)


@router.post("/refresh", dependencies=[Depends(require_interactive_session)])
def refresh_access_token(
    username: str = Depends(get_current_user),
    token: str | None = Depends(optional_oauth2),
) -> Any:
    """Renouvelle un jeton de session encore valide (l'interface l'appelle quand il expire bientôt).

    La durée d'inactivité reste bornée par l'expiration du jeton ; la durée totale de la session l'est
    par `SESSION_MAX_HOURS` depuis la connexion par mot de passe (`auth_time`). Jamais pour un jeton MCP.
    """
    return service.refresh_access_token(username, token)
