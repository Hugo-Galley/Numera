from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

class AdminProfile(BaseModel):
    username: str
    profile_picture_url: Optional[str] = None
    mcp_enabled: bool = True

class AdminProfileUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    # Obligatoire pour changer l'identifiant ou le mot de passe
    current_password: Optional[str] = None
    profile_picture_url: Optional[str] = None
    mcp_enabled: Optional[bool] = None


class McpTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


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
