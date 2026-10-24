from typing import Generator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import ValidationError

from app.core.config import settings
from app.core.mcp_tokens import authenticate_mcp_token, is_mcp_token
from app.db.session import SessionLocal

from sqlalchemy.orm import Session
from app.db.system_settings import get_setting

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/auth/token"
)
optional_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


MCP_ALLOWED_METHODS = {"GET", "HEAD"}


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    current_admin = get_setting(db, "admin_username", settings.ADMIN_USERNAME)
    # Token MCP généré depuis l'interface (agents IA) : lecture seule, hors /admin
    if is_mcp_token(token):
        if not authenticate_mcp_token(db, token):
            raise credentials_exception
        if request.method not in MCP_ALLOWED_METHODS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès MCP en lecture seule",
            )
        return current_admin

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub"]},  # un jeton sans expiration ne serait jamais périmé
        )
        token_data = payload.get("sub")
        if token_data is None:
            raise credentials_exception
        # Un changement de mot de passe invalide les sessions ouvertes avant lui
        valid_after = int(get_setting(db, "auth_valid_after", "0") or 0)
        if int(payload.get("auth_time") or 0) < valid_after:
            raise credentials_exception
    except (jwt.PyJWTError, ValidationError):
        raise credentials_exception
    
    # In single user mode, we check if it's the current admin username
    if token_data != current_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not authorized",
        )
    
    return token_data


def require_interactive_session(token: str | None = Depends(optional_oauth2)) -> None:
    """Refuse les tokens MCP : réservé à l'interface (profil, reset, gestion des tokens).

    L'authentification elle-même reste faite par `get_current_user` au niveau du router.
    """
    if is_mcp_token(token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action réservée à l'interface web",
        )
