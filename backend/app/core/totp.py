"""TOTP (RFC 6238 : SHA-1, 6 chiffres, pas de 30 s), compatible Google Authenticator et équivalents.

Implémenté avec la bibliothèque standard ; seul le QR code passe par `segno`.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import jwt
import segno
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.system_settings import get_setting

PERIOD = 30
DIGITS = 6
# Tolérance d'un pas de part et d'autre (horloge du téléphone légèrement décalée)
VALID_WINDOW = 1
ISSUER = "Numera"
SECRET_KEY_SETTING = "totp_secret"
MFA_TOKEN_TTL_SECONDS = 300


def generate_secret() -> str:
    """Secret base32 de 160 bits (taille recommandée par la RFC 4226)."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def current_step(now: float | None = None) -> int:
    return int((time.time() if now is None else now) // PERIOD)


def code_for(secret: str, now: float | None = None) -> str:
    return _code_at(secret, current_step(now))


def verify(secret: str, code: str, last_step: int = -1, now: float | None = None) -> int | None:
    """Pas de temps du code s'il est valide et postérieur à `last_step` (un code déjà utilisé est
    refusé, même encore dans sa fenêtre de validité), sinon None."""
    code = "".join(code.split())
    if len(code) != DIGITS or not code.isdigit():
        return None
    step = current_step(now)
    for candidate in range(step - VALID_WINDOW, step + VALID_WINDOW + 1):
        if candidate > last_step and hmac.compare_digest(_code_at(secret, candidate), code):
            return candidate
    return None


def provisioning_uri(secret: str, account: str) -> str:
    label = quote(f"{ISSUER}:{account}", safe=":@")
    query = urlencode({"secret": secret, "issuer": ISSUER, "algorithm": "SHA1", "digits": DIGITS, "period": PERIOD})
    return f"otpauth://totp/{label}?{query}"


def qr_svg_data_uri(uri: str) -> str:
    return segno.make(uri, error="m").svg_data_uri(scale=5, border=2)


def generate_recovery_codes(count: int = 10) -> list[str]:
    """Codes de secours à usage unique, format `xxxxx-xxxxx` (base32 minuscule, sans ambiguïté 0/O)."""
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(alphabet) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(normalize_recovery_code(code).encode()).hexdigest()


def normalize_recovery_code(code: str) -> str:
    return "".join(ch for ch in code.lower() if ch.isalnum())


def is_enabled(db: Session) -> bool:
    return bool(get_setting(db, SECRET_KEY_SETTING))


def create_mfa_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"purpose": "totp", "u": username, "iat": now, "exp": now + timedelta(seconds=MFA_TOKEN_TTL_SECONDS)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
