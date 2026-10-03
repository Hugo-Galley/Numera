from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import security
from app.core.config import settings
from app.core.migrations import run_migrations
from app.core.seeds import seed_default_categories
from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db
from app.db.system_settings import get_setting, set_setting
from app.schemas.admin import AdminProfile, AdminProfileUpdate

router = APIRouter(prefix="/admin", tags=["admin"])

MIN_PASSWORD_LENGTH = 8


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
    if profile_in.profile_picture_url is not None:
        set_setting(db, "profile_picture_url", profile_in.profile_picture_url)
    if profile_in.mcp_enabled is not None:
        set_setting(db, "mcp_enabled", "true" if profile_in.mcp_enabled else "false")
    return get_admin_profile(db, current_user)


class ResetDatabaseRequest(BaseModel):
    confirm: bool = False
    confirmation_code: str | None = None


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
