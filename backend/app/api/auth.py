from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.db.system_settings import get_setting

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Try to get admin credentials from database
    db_username = get_setting(db, "admin_username", settings.ADMIN_USERNAME)
    db_password_hash = get_setting(db, "admin_password_hash", settings.ADMIN_PASSWORD_HASH)

    if form_data.username != db_username:
        logger.warning(f"Failed login attempt: incorrect username '{form_data.username}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )
    
    if not security.verify_password(form_data.password, db_password_hash):
        logger.warning(f"Failed login attempt for user '{form_data.username}': incorrect password")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )
    
    logger.info(f"Successful login for user '{form_data.username}'")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            form_data.username, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
