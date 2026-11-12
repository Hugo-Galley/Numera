from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_user, require_interactive_session
from app.db.session import get_db
from app.schemas.admin import (
    AdminProfile,
    AdminProfileUpdate,
    BackupRunResult,
    BackupStatus,
    LoginEventRead,
    McpTokenCreate,
    McpTokenCreated,
    McpTokenRead,
)
from app.schemas.common import OkResponse, StatusResponse
from app.services.systeme import admin as service

if TYPE_CHECKING:
    from app.models.login_event import LoginEvent
    from app.models.mcp_token import McpToken

# Les tokens MCP n'ont pas accès à /admin : un agent ne peut ni changer le mot de passe, ni vider
# la base, ni se créer d'autres tokens.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_interactive_session)])


class ResetDatabaseRequest(BaseModel):
    confirm: bool = False
    confirmation_code: str | None = None
    current_password: str | None = None


@router.get("/profile", response_model=AdminProfile)
def get_admin_profile(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)) -> AdminProfile:
    return service.get_admin_profile(db)


@router.put("/profile", response_model=AdminProfile)
def update_admin_profile(
    profile_in: AdminProfileUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> AdminProfile:
    return service.update_admin_profile(db, profile_in)


@router.get("/login-events", response_model=list[LoginEventRead])
def list_login_events(limit: int = 50, db: Session = Depends(get_db)) -> "list[LoginEvent]":
    """Dernières tentatives de connexion, réussies ou non (les plus récentes d'abord)."""
    return service.list_login_events(db, limit)


@router.post("/logout-all", response_model=OkResponse)
def logout_all_sessions(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Invalide toutes les sessions ouvertes, y compris celle-ci (les tokens MCP ne sont pas concernés)."""
    return service.logout_all_sessions(db)


@router.get("/mcp-tokens", response_model=list[McpTokenRead])
def list_mcp_tokens(db: Session = Depends(get_db)) -> "list[McpToken]":
    return service.list_mcp_tokens(db)


@router.post("/mcp-tokens", response_model=McpTokenCreated, status_code=201)
def create_mcp_token(payload: McpTokenCreate, db: Session = Depends(get_db)) -> McpTokenCreated:
    return service.create_mcp_token(db, payload)


@router.delete("/mcp-tokens/{token_id}", status_code=204)
def revoke_mcp_token(token_id: int, db: Session = Depends(get_db)) -> None:
    service.revoke_mcp_token(db, token_id)


@router.post("/reset-database", response_model=StatusResponse)
def reset_database(
    payload: ResetDatabaseRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> dict[str, Any]:
    return service.reset_database(db, payload.confirm, payload.confirmation_code, payload.current_password)


@router.post("/backup/run", response_model=BackupRunResult)
def run_backup_now(current_user: str = Depends(get_current_user)) -> dict[str, Any]:
    """Lance `scripts/backup.py` (sauvegarde chiffrée + envoi GitHub si configuré) et attend la fin."""
    return service.run_backup_now()


@router.get("/backup/status", response_model=BackupStatus)
def get_backup_status() -> BackupStatus:
    """Dernière sauvegarde, envoi GitHub et retard éventuel (lus dans BACKUP_DIR)."""
    return service.get_backup_status()
