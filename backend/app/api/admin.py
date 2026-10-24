import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_interactive_session
from app.core import security
from app.core.backup import snapshot_database
from app.core.config import settings
from app.core.logging import get_logger
from app.core.mcp_tokens import generate_token, hash_token
from app.core.migrations import run_migrations
from app.core.seeds import seed_default_categories
from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db
from app.db.system_settings import get_setting, set_setting
from app.models.mcp_token import McpToken
from app.schemas.admin import AdminProfile, AdminProfileUpdate, McpTokenCreate, McpTokenCreated, McpTokenRead

# Les tokens MCP n'ont pas accès à /admin : un agent ne peut ni changer le mot de passe, ni vider
# la base, ni se créer d'autres tokens.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_interactive_session)])

logger = get_logger(__name__)

MIN_PASSWORD_LENGTH = 8


def _require_current_password(db: Session, password: str | None) -> None:
    """400 (jamais 401/403 : le client API déconnecte sur ces codes) si le mot de passe est absent ou faux."""
    current_hash = get_setting(db, "admin_password_hash", settings.ADMIN_PASSWORD_HASH)
    if not password or not security.verify_password(password, current_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")


@router.get("/profile", response_model=AdminProfile)
def get_admin_profile(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return AdminProfile(
        username=get_setting(db, "admin_username", settings.ADMIN_USERNAME),
        profile_picture_url=get_setting(db, "profile_picture_url"),
        mcp_enabled=get_setting(db, "mcp_enabled", "true").lower() == "true",
    )


@router.put("/profile", response_model=AdminProfile)
def update_admin_profile(
    profile_in: AdminProfileUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    current_username = get_setting(db, "admin_username", settings.ADMIN_USERNAME)
    username_changed = bool(profile_in.username) and profile_in.username != current_username
    if username_changed or profile_in.password:
        # Un token volé ne doit pas suffire à prendre le contrôle du compte
        current_hash = get_setting(db, "admin_password_hash", settings.ADMIN_PASSWORD_HASH)
        if not profile_in.current_password or not security.verify_password(profile_in.current_password, current_hash):
            raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    if profile_in.password and len(profile_in.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères",
        )

    if profile_in.username:
        set_setting(db, "admin_username", profile_in.username)
    if profile_in.password:
        set_setting(db, "admin_password_hash", security.get_password_hash(profile_in.password))
        # Les sessions ouvertes avant ce changement ne sont plus valides (un jeton volé ne survit pas)
        set_setting(db, "auth_valid_after", str(int(time.time())))
    if profile_in.profile_picture_url is not None:
        set_setting(db, "profile_picture_url", profile_in.profile_picture_url)
    if profile_in.mcp_enabled is not None:
        set_setting(db, "mcp_enabled", "true" if profile_in.mcp_enabled else "false")
    return get_admin_profile(db, current_user)


@router.get("/mcp-tokens", response_model=list[McpTokenRead])
def list_mcp_tokens(db: Session = Depends(get_db)):
    return db.query(McpToken).order_by(McpToken.created_at.desc()).all()


@router.post("/mcp-tokens", response_model=McpTokenCreated, status_code=201)
def create_mcp_token(payload: McpTokenCreate, db: Session = Depends(get_db)):
    _require_current_password(db, payload.current_password)
    token = generate_token()
    record = McpToken(name=payload.name.strip(), token_hash=hash_token(token), token_prefix=token[:8])
    db.add(record)
    db.commit()
    db.refresh(record)
    return McpTokenCreated(**McpTokenRead.model_validate(record).model_dump(), token=token)


@router.delete("/mcp-tokens/{token_id}", status_code=204)
def revoke_mcp_token(token_id: int, db: Session = Depends(get_db)):
    record = db.get(McpToken, token_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Token introuvable")
    db.delete(record)
    db.commit()


class ResetDatabaseRequest(BaseModel):
    confirm: bool = False
    confirmation_code: str | None = None
    current_password: str | None = None


@router.post("/reset-database")
def reset_database(
    payload: ResetDatabaseRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    if payload.confirmation_code != "EFFACER":
        raise HTTPException(status_code=400, detail="Invalid confirmation code. Please type 'EFFACER' to confirm.")
    _require_current_password(db, payload.current_password)

    # Filet de sécurité : instantané de la base avant de tout effacer
    db_file = engine.url.database
    if engine.url.get_backend_name() == "sqlite" and db_file and Path(db_file).exists():
        try:
            backup = snapshot_database(db_file, Path(db_file).resolve().parent / "backups", prefix="pre-reset")
            logger.info("Instantané avant reset : %s", backup.name)
        except Exception:
            logger.exception("Instantané avant reset impossible : reset annulé")
            raise HTTPException(status_code=500, detail="Sauvegarde préalable impossible, réinitialisation annulée")

    db.close()
    with engine.connect() as connection:
        # Les FK circulaires (transactions <-> investment_transactions) empêchent un DROP
        # ordonné quand les FK sont actives ; on les suspend le temps du reset.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(bind=connection)
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        connection.commit()

    run_migrations()
    seed_db = SessionLocal()
    try:
        seed_default_categories(seed_db)
    finally:
        seed_db.close()

    return {"status": "ok"}
