from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AdminProfile(BaseModel):
    username: str
    profile_picture_url: Optional[str] = None
    mcp_enabled: bool = True
    # Ouvrir l'application montants masqués (mode confidentialité), sur tous les appareils
    privacy_on_start: bool = False

class AdminProfileUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    # Obligatoire pour changer l'identifiant ou le mot de passe
    current_password: Optional[str] = None
    profile_picture_url: Optional[str] = None
    mcp_enabled: Optional[bool] = None
    privacy_on_start: Optional[bool] = None


class McpTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # Obligatoire : un token MCP donne un accès durable en lecture à toutes les données
    current_password: Optional[str] = None


class McpTokenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    token_prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None


class McpTokenCreated(McpTokenRead):
    # Valeur en clair, renvoyée une seule fois à la création
    token: str


class LoginEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    method: str
    success: bool
    reason: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None


class BackupStatus(BaseModel):
    configured: bool
    last_backup_at: Optional[datetime] = None
    last_backup_file: Optional[str] = None
    encrypted: Optional[bool] = None
    backup_count: int = 0
    last_auto_success_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    github_configured: bool = False
    github_last_sync_at: Optional[datetime] = None
    github_error: Optional[str] = None
    stale: bool = False
