from typing import Optional
from pydantic import BaseModel

class AdminProfile(BaseModel):
    username: str
    profile_picture_url: Optional[str] = None
    mcp_enabled: bool = True

class AdminProfileUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    profile_picture_url: Optional[str] = None
    mcp_enabled: Optional[bool] = None
