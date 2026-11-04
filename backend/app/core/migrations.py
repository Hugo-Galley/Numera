import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Sauvegardes d'avant migration conservées (les plus récentes) ; hors `suivi_budget_*`, donc hors rotation
# quotidienne de scripts/backup.py et hors envoi GitHub.
PRE_MIGRATION_KEEP = 5
INSECURE_BACKUP_KEYS = {"", "generate-a-fernet-key-using-python"}


def _current_revision(db_path: str) -> str | None:
    """Révision Alembic de la base ; None si la base est vide ou sans table de suivi.

    Lève `LookupError` si la base contient des tables mais aucune révision (schéma jamais estampillé).
    """
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not tables:
            return None
        if "alembic_version" not in tables:
            raise LookupError("unstamped")
        row = con.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None
    finally:
        con.close()


def backup_before_migration(db_path: str, backend_root: Path) -> Path | None:
    """Copie la base dans BACKUP_DIR quand les migrations vont changer son schéma ; None si inutile.

    Une mise à jour peut modifier la base de façon irréversible : sans cette copie, le seul retour arrière
    serait la sauvegarde quotidienne (jusqu'à 24 h de données perdues).
    """
    if not Path(db_path).is_file() or Path(db_path).stat().st_size == 0:
        return None
    try:
        current = _current_revision(db_path)
    except LookupError:
        current = "unstamped"
    if current is None:
        return None
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    head = ScriptDirectory.from_config(cfg).get_current_head()
    if current == head:
        return None

    backup_dir = Path(os.getenv("BACKUP_DIR") or Path(db_path).parent.parent / "backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / f"pre_migration_{current}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    try:
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
            check = target.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            target.close()
    finally:
        source.close()
    if check != "ok":
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"Pre-migration backup integrity check failed: {check}")

    key = os.getenv("BACKUP_KEY", "")
    if key not in INSECURE_BACKUP_KEYS:
        from cryptography.fernet import Fernet

        encrypted = dest.with_name(dest.name + ".enc")
        encrypted.write_bytes(Fernet(key.encode()).encrypt(dest.read_bytes()))
        dest.unlink()
        dest = encrypted

    old = sorted(backup_dir.glob("pre_migration_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in old[PRE_MIGRATION_KEEP:]:
        if stale != dest:
            stale.unlink(missing_ok=True)
    logger.info(f"Pre-migration backup written to {dest} (schema {current} -> {head})")
    return dest


def run_migrations() -> None:
    logger.info("Starting database migrations...")
    backend_root = Path(__file__).resolve().parents[2]

    # We use subprocess to run alembic to avoid any in-process locking or logging conflicts
    try:
        # 1. Ensure WAL mode is enabled first
        import sqlite3
        if settings.database_url.startswith("sqlite"):
            db_path = settings.database_url.replace("sqlite:///", "")
            # Handle absolute path (sqlite:////app/...)
            if db_path.startswith("/"):
                pass
            else:
                db_path = str(backend_root / db_path)

            logger.info(f"Target DB path for WAL: {db_path}")
            try:
                conn = sqlite3.connect(db_path, timeout=30)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.close()
                logger.info("SQLite WAL mode enabled.")
            except Exception as e:
                logger.warning(f"Could not enable WAL mode via sqlite3: {e}")

            # 1b. Sauvegarde de la base avant toute migration qui changerait le schéma
            try:
                backup_before_migration(db_path, backend_root)
            except Exception as e:
                logger.error(f"Pre-migration backup failed: {e}", exc_info=True)
                raise RuntimeError(
                    "Pre-migration backup failed; refusing to migrate without a safety copy. "
                    "Check BACKUP_DIR (writable?) and BACKUP_KEY, then restart."
                ) from e

        # 2. Run alembic upgrade head
        env = {**os.environ, "PYTHONPATH": str(backend_root)}
        logger.info(f"Executing: alembic upgrade head in {backend_root}")
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(backend_root),
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode == 0:
            logger.info("Migrations successful:\n" + result.stdout)
            return

        # Pas de `alembic stamp head` automatique : marquer le schéma « à jour » sans l'avoir
        # migré masque des colonnes manquantes et casse l'application plus tard, sans explication.
        logger.error(f"Migrations failed (exit {result.returncode}):\n" + result.stderr)
        raise RuntimeError(
            "Database migration failed; refusing to start with an out-of-date schema. "
            "See the log above (restore a backup or fix the revision, then restart)."
        )
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during migration subprocess: {e}", exc_info=True)
        raise


