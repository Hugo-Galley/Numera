"""Schémas de l'authentification : double authentification TOTP et passkeys."""
from typing import Any

from pydantic import BaseModel


class TotpStatus(BaseModel):
    enabled: bool
    recovery_codes_left: int


class TotpSetupBody(BaseModel):
    current_password: str


class TotpSetup(BaseModel):
    secret: str
    otpauth_uri: str
    qr_svg: str


class CodeBody(BaseModel):
    code: str


class DisableBody(BaseModel):
    current_password: str
    code: str


class RecoveryCodes(BaseModel):
    recovery_codes: list[str]


class TotpLoginBody(BaseModel):
    mfa_token: str
    code: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str


class ReauthBody(BaseModel):
    """Un jeton de session volé ne doit pas suffire à ajouter ou retirer une passkey."""
    current_password: str | None = None
    code: str | None = None


class RegisterVerifyBody(ReauthBody):
    state: str
    credential: dict[str, Any]
    name: str | None = None


class LoginVerifyBody(BaseModel):
    state: str
    credential: dict[str, Any]
