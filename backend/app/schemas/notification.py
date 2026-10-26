from typing import Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["low", "medium", "high"]


class NotificationSettingsRead(BaseModel):
    """Réglages des notifications ; les jetons sont masqués (`••••` + 4 derniers caractères)."""
    ntfy_enabled: bool
    ntfy_server: str
    ntfy_topic: str
    ntfy_token: str
    telegram_enabled: bool
    telegram_bot_token: str
    telegram_chat_id: str
    min_severity: Severity
    weekly_digest: bool
    hide_amounts: bool
    public_url: str


class NotificationSettingsUpdate(BaseModel):
    ntfy_enabled: bool | None = None
    ntfy_server: str | None = Field(default=None, max_length=200)
    ntfy_topic: str | None = Field(default=None, max_length=120)
    ntfy_token: str | None = Field(default=None, max_length=200)
    telegram_enabled: bool | None = None
    telegram_bot_token: str | None = Field(default=None, max_length=200)
    telegram_chat_id: str | None = Field(default=None, max_length=64)
    min_severity: Severity | None = None
    weekly_digest: bool | None = None
    hide_amounts: bool | None = None
    public_url: str | None = Field(default=None, max_length=300)

    @field_validator("ntfy_server", "public_url")
    @classmethod
    def _http_url(cls, value: str | None) -> str | None:
        if value and not value.strip().lower().startswith(("http://", "https://")):
            raise ValueError("L'adresse doit commencer par http:// ou https://")
        return value


class NotificationTestRequest(BaseModel):
    channel: Literal["ntfy", "telegram"]


class NotificationTestResult(BaseModel):
    channel: str
    delivered: bool
