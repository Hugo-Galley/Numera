"""Administration mono-utilisateur : profil, sessions, jetons MCP, remise à zéro, sauvegardes.

Les refus liés au mot de passe sont des 400, jamais 401/403 : le client API déconnecte sur ces codes.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import security
from app.integrations.backup import backup_status, snapshot_database
from app.core.config import settings
from app.core.errors import BusinessRuleError, ExternalTimeoutError, InternalError, InvalidOperationError, NotFoundError
from app.core.logging import get_logger
from app.core.mcp_tokens import generate_token, hash_token
from app.core.migrations import run_migrations
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.db.system_settings import get_setting, set_setting
from app.models.login_event import LoginEvent
from app.models.mcp_token import McpToken
from app.repositories.systeme import admin as repo
from app.schemas.admin import AdminProfile, AdminProfileUpdate, BackupStatus, McpTokenCreate, McpTokenCreated, McpTokenRead
from app.services.systeme.seeds import seed_default_categories

logger = get_logger(__name__)

MIN_PASSWORD_LENGTH = 8
RESET_CONFIRMATION_CODE = "EFFACER"
BACKUP_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "backup.py"
BACKUP_TIMEOUT_SECONDS = 180


def _password_ok(db: Session, password: str | None) -> bool:
    current_hash = get_setting(db, "admin_password_hash", settings.ADMIN_PASSWORD_HASH)
    return bool(password) and security.verify_password(password, current_hash)


def _require_current_password(db: Session, password: str | None) -> None:
    if not _password_ok(db, password):
        raise InvalidOperationError("Mot de passe actuel incorrect")


def get_admin_profile(db: Session) -> AdminProfile:
    return AdminProfile(
        username=get_setting(db, "admin_username", settings.ADMIN_USERNAME),
        profile_picture_url=get_setting(db, "profile_picture_url"),
        mcp_enabled=get_setting(db, "mcp_enabled", "true").lower() == "true",
        privacy_on_start=get_setting(db, "ui.privacy_on_start", "false").lower() == "true",
    )


def update_admin_profile(db: Session, profile_in: AdminProfileUpdate) -> AdminProfile:
    current_username = get_setting(db, "admin_username", settings.ADMIN_USERNAME)
    username_changed = bool(profile_in.username) and profile_in.username != current_username
    if username_changed or profile_in.password:
        # Un token volé ne doit pas suffire à prendre le contrôle du compte
        _require_current_password(db, profile_in.current_password)
    if profile_in.password and len(profile_in.password) < MIN_PASSWORD_LENGTH:
        raise BusinessRuleError(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères")

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
    if profile_in.privacy_on_start is not None:
        set_setting(db, "ui.privacy_on_start", "true" if profile_in.privacy_on_start else "false")
    return get_admin_profile(db)


def list_login_events(db: Session, limit: int) -> list[LoginEvent]:
    """Dernières tentatives de connexion, réussies ou non (les plus récentes d'abord)."""
    return repo.recent_login_events(db, max(1, min(limit, 200)))


def logout_all_sessions(db: Session) -> dict:
    """Invalide toutes les sessions ouvertes, y compris celle-ci (les tokens MCP ne sont pas concernés)."""
    set_setting(db, "auth_valid_after", str(int(time.time()) + 1))
    logger.info("Toutes les sessions ont été déconnectées")
    return {"ok": True}


def list_mcp_tokens(db: Session) -> list[McpToken]:
    return repo.mcp_tokens(db)


def create_mcp_token(db: Session, payload: McpTokenCreate) -> McpTokenCreated:
    _require_current_password(db, payload.current_password)
    token = generate_token()
    record = McpToken(name=payload.name.strip(), token_hash=hash_token(token), token_prefix=token[:8])
    db.add(record)
    db.commit()
    db.refresh(record)
    return McpTokenCreated(**McpTokenRead.model_validate(record).model_dump(), token=token)


def revoke_mcp_token(db: Session, token_id: int) -> None:
    record = repo.get_mcp_token(db, token_id)
    if record is None:
        raise NotFoundError("Token introuvable")
    db.delete(record)
    db.commit()


def _snapshot_before_reset() -> None:
    """Filet de sécurité : instantané de la base SQLite avant de tout effacer (sinon, reset annulé)."""
    db_file = engine.url.database
    if engine.url.get_backend_name() != "sqlite" or not db_file or not Path(db_file).exists():
        return
    try:
        backup = snapshot_database(db_file, Path(db_file).resolve().parent / "backups", prefix="pre-reset")
        logger.info("Instantané avant reset : %s", backup.name)
    except Exception:
        logger.exception("Instantané avant reset impossible : reset annulé")
        raise InternalError("Sauvegarde préalable impossible, réinitialisation annulée")


def reset_database(db: Session, confirm: bool, confirmation_code: str | None, current_password: str | None) -> dict:
    if not confirm:
        raise InvalidOperationError("Confirmation required")
    if confirmation_code != RESET_CONFIRMATION_CODE:
        raise InvalidOperationError("Invalid confirmation code. Please type 'EFFACER' to confirm.")
    _require_current_password(db, current_password)
    _snapshot_before_reset()

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


def run_backup_now() -> dict:
    """Lance `scripts/backup.py` (sauvegarde chiffrée + envoi GitHub si configuré) et attend la fin."""
    try:
        result = subprocess.run(
            [sys.executable, str(BACKUP_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=BACKUP_TIMEOUT_SECONDS,
            env={**os.environ, "BACKUP_TRIGGER": "manual"},
        )
    except subprocess.TimeoutExpired:
        raise ExternalTimeoutError("La sauvegarde a dépassé le délai imparti")
    if result.returncode != 0:
        errors = [line for line in result.stderr.splitlines() if "ERROR" in line]
        detail = errors[-1].split("ERROR - ", 1)[-1] if errors else "Échec de la sauvegarde"
        logger.error("Sauvegarde manuelle en échec (code %s) : %s", result.returncode, detail)
        raise InternalError(detail)  # 500 et non 401/403 : le client API déconnecte sur ces codes
    return {"ok": True, "github": bool(os.getenv("GITHUB_BACKUP_REPO", "").strip())}


def get_backup_status() -> BackupStatus:
    """Dernière sauvegarde, envoi GitHub et retard éventuel (lus dans BACKUP_DIR)."""
    return backup_status()
