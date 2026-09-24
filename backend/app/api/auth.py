from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.logging import get_logger
from app.core.login_rate_limit import LoginRateLimiter
from app.db.session import get_db
from app.db.system_settings import get_setting

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
login_rate_limiter = LoginRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_SECONDS,
    lockout_seconds=settings.LOGIN_LOCKOUT_SECONDS,
)


def _client_key(request: Request, username: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{username.casefold()}"


@router.post("/token")
def login_access_token(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    key = _client_key(request, form_data.username)
    if not login_rate_limiter.is_allowed(key):
        logger.warning("Login temporarily blocked due to repeated failed attempts")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(settings.LOGIN_LOCKOUT_SECONDS)},
        )

    # Try to get admin credentials from database
    db_username = get_setting(db, "admin_username", settings.ADMIN_USERNAME)
    db_password_hash = get_setting(db, "admin_password_hash", settings.ADMIN_PASSWORD_HASH)

    username_valid = (form_data.username == db_username)
    # Dummy bcrypt hash to make verification time constant and prevent timing attacks
    dummy_hash = "$2b$12$e8k8W8eD.2eC/W3W2c/UGeFm3XWzM8/8G6hWj.e4R2q3Z0r4c8h2W"
    hash_to_verify = db_password_hash if username_valid else dummy_hash
    password_valid = security.verify_password(form_data.password, hash_to_verify)

    if not username_valid or not password_valid:
        login_rate_limiter.record_failure(key)
        logger.warning("Failed login attempt: invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    login_rate_limiter.reset(key)
    logger.info("Successful login")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            form_data.username, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
