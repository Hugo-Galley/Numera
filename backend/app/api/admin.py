from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.migrations import run_migrations
from app.core.seeds import seed_default_categories
from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db

from app.api.deps import get_current_user
from app.core import security
from app.core.config import settings
from app.db.system_settings import get_setting, set_setting
from app.schemas.admin import AdminProfile, AdminProfileUpdate

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/profile", response_model=AdminProfile)
def get_admin_profile(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    return AdminProfile(
        username=get_setting(db, "admin_username", settings.ADMIN_USERNAME),
        profile_picture_url=get_setting(db, "profile_picture_url"),
        mcp_enabled=get_setting(db, "mcp_enabled", "true").lower() == "true"
    )

@router.put("/profile", response_model=AdminProfile)
def update_admin_profile(
    profile_in: AdminProfileUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    if profile_in.username:
        set_setting(db, "admin_username", profile_in.username)
    
    if profile_in.password:
        hashed_password = security.get_password_hash(profile_in.password)
        set_setting(db, "admin_password_hash", hashed_password)
    
    if profile_in.profile_picture_url is not None:
        set_setting(db, "profile_picture_url", profile_in.profile_picture_url)
    
    if profile_in.mcp_enabled is not None:
        set_setting(db, "mcp_enabled", "true" if profile_in.mcp_enabled else "false")
    
    return get_admin_profile(db, current_user)


class ResetDatabaseRequest(BaseModel):
    confirm: bool = False
    confirmation_code: str | None = None


@router.post("/reset-database")
def reset_database(payload: ResetDatabaseRequest, db: Session = Depends(get_db)):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    
    if payload.confirmation_code != "EFFACER":
        raise HTTPException(status_code=400, detail="Invalid confirmation code. Please type 'EFFACER' to confirm.")

    db.close()

    Base.metadata.drop_all(bind=engine)
    with engine.connect() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        connection.commit()

    run_migrations()
    seed_db = SessionLocal()
    try:
        seed_default_categories(seed_db)
    finally:
        seed_db.close()

    return {"status": "ok"}


class MCPInstallRequest(BaseModel):
    client: str # "claude", "cursor", "cursor_project", "cline", "roo_code"


@router.post("/mcp/install")
def install_mcp_config(
    payload: MCPInstallRequest,
    current_user: str = Depends(get_current_user)
):
    import os
    import json
    from pathlib import Path
    
    api_dir = Path(__file__).parent.resolve()
    project_root = api_dir.parent.parent.parent.resolve()
    
    server_path = str(project_root / "mcp-server" / "server.py")
    db_path = str(project_root / "backend" / "data" / "suivi_budget.db")
    
    config_data = {
        "mcpServers": {
            "numera-mcp": {
                "command": "python3",
                "args": [server_path],
                "env": {
                    "MCP_DB_PATH": db_path
                }
            }
        }
    }
    
    home = os.path.expanduser("~")
    target_path = None
    client_name = payload.client.lower()
    
    if client_name == "claude":
        if os.name == "nt":
            target_path = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
        else:
            try:
                # macOS
                if os.uname().sysname == "Darwin":
                    target_path = Path(home) / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
                else: # Linux
                    target_path = Path(home) / ".config" / "Claude" / "claude_desktop_config.json"
            except AttributeError:
                # Fallback if uname is not available
                target_path = Path(home) / ".config" / "Claude" / "claude_desktop_config.json"
            
    elif client_name == "cursor":
        if os.name == "nt":
            target_path = Path(os.environ.get("APPDATA", "")) / "Cursor" / "User" / "globalStorage" / "moondream.cursor-mcp" / "mcpServers.json"
        else:
            try:
                if os.uname().sysname == "Darwin":
                    target_path = Path(home) / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "moondream.cursor-mcp" / "mcpServers.json"
                else:
                    target_path = Path(home) / ".config" / "Cursor" / "User" / "globalStorage" / "moondream.cursor-mcp" / "mcpServers.json"
            except AttributeError:
                target_path = Path(home) / ".config" / "Cursor" / "User" / "globalStorage" / "moondream.cursor-mcp" / "mcpServers.json"
            
    elif client_name == "cursor_project":
        cursor_dir = project_root / ".cursor"
        target_path = cursor_dir / "mcp.json"
        
    elif client_name == "cline":
        if os.name == "nt":
            target_path = Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"
        else:
            try:
                if os.uname().sysname == "Darwin":
                    target_path = Path(home) / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"
                else:
                    target_path = Path(home) / ".config" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"
            except AttributeError:
                target_path = Path(home) / ".config" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"
            
    elif client_name == "roo_code":
        if os.name == "nt":
            target_path = Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "globalStorage" / "roovetlik.roo-cline" / "settings" / "cline_mcp_settings.json"
        else:
            try:
                if os.uname().sysname == "Darwin":
                    target_path = Path(home) / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "roovetlik.roo-cline" / "settings" / "cline_mcp_settings.json"
                else:
                    target_path = Path(home) / ".config" / "Code" / "User" / "globalStorage" / "roovetlik.roo-cline" / "settings" / "cline_mcp_settings.json"
            except AttributeError:
                target_path = Path(home) / ".config" / "Code" / "User" / "globalStorage" / "roovetlik.roo-cline" / "settings" / "cline_mcp_settings.json"
            
    else:
        raise HTTPException(status_code=400, detail=f"Client '{payload.client}' non supporté.")
        
    if not target_path:
        return {
            "success": False,
            "message": "Impossible de déterminer le chemin cible sur ce système d'exploitation.",
            "config_content": config_data
        }
        
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing_data = {}
        if target_path.exists():
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                pass
                
        if "mcpServers" not in existing_data:
            existing_data["mcpServers"] = {}
        
        existing_data["mcpServers"]["numera-mcp"] = config_data["mcpServers"]["numera-mcp"]
        
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2)
            
        return {
            "success": True,
            "message": f"Configuration installée avec succès dans : {target_path}",
            "config_written": str(target_path),
            "config_content": config_data
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Échec de l'écriture automatique : {str(e)}. Vous pouvez copier-coller la configuration manuellement.",
            "config_content": config_data
        }

