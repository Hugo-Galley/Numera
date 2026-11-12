from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminProfile(BaseModel):
    username: str
    profile_picture_url: str | None = None
    mcp_enabled: bool = True
    # Ouvrir l'application montants masqués (mode confidentialité), sur tous les appareils
    privacy_on_start: bool = False

class AdminProfileUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    # Obligatoire pour changer l'identifiant ou le mot de passe
    current_password: str | None = None
    profile_picture_url: str | None = None
    mcp_enabled: bool | None = None
    privacy_on_start: bool | None = None


class McpTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # Obligatoire : un token MCP donne un accès durable en lecture à toutes les données
    current_password: str | None = None


class McpTokenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    token_prefix: str
    created_at: datetime
    last_used_at: datetime | None = None


class McpTokenCreated(McpTokenRead):
    # Valeur en clair, renvoyée une seule fois à la création
    token: str


class LoginEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    method: str
    success: bool
    reason: str | None = None
    ip: str | None = None
    user_agent: str | None = None


class BackupStatus(BaseModel):
    configured: bool
    last_backup_at: datetime | None = None
    last_backup_file: str | None = None
    encrypted: bool | None = None
    backup_count: int = 0
    last_auto_success_at: datetime | None = None
    last_attempt_at: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None
    github_configured: bool = False
    github_last_sync_at: datetime | None = None
    github_error: str | None = None
    stale: bool = False


class BackupRunResult(BaseModel):
    ok: bool
    github: bool  # envoi GitHub configuré
