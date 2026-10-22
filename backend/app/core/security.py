import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any, Union

import jwt

from app.core.config import settings


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None, auth_time: int | None = None
) -> str:
    """JWT de session. `auth_time` (horodatage Unix de la connexion par mot de passe) est conservé
    d'un renouvellement à l'autre pour borner la durée totale d'une session."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "auth_time": auth_time or int(now.timestamp())}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
