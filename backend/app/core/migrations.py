from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def run_migrations() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    alembic_ini = backend_root / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)

    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False, "timeout": 30} if settings.database_url.startswith("sqlite") else {},
    )
    
    # Try to enable WAL mode for SQLite to prevent locking issues
    if settings.database_url.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        except Exception as e:
            logger.warning(f"Could not enable WAL mode: {e}")
    
    tables_exist = False
    alembic_ready = False
    
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())
            tables_exist = len(tables) > 0
            if "alembic_version" in tables:
                try:
                    result = connection.exec_driver_sql("SELECT version_num FROM alembic_version")
                    row = result.fetchone()
                    if row:
                        alembic_ready = True
                except Exception:
                    pass
    finally:
        engine.dispose()

    try:
        if not tables_exist:
            logger.info("Database is empty, running 'command.upgrade(cfg, head)'...")
            command.upgrade(cfg, "head")
            logger.info("Upgrade head successful.")
        elif not alembic_ready:
            logger.info("Tables exist but no alembic version found, running 'command.stamp(cfg, head)'...")
            command.stamp(cfg, "head")
            logger.info("Stamp head successful.")
        else:
            logger.info("Database is ready, checking for pending migrations with 'command.upgrade(cfg, head)'...")
            command.upgrade(cfg, "head")
            logger.info("Check/Upgrade head successful.")
    except Exception as e:
        error_str = str(e)
        if "Can't locate revision identified by" in error_str:
            logger.warning(f"Database at unknown revision: {error_str}. Stamping head.")
            command.stamp(cfg, "head")
        else:
            logger.error(f"Migration error: {e}. Continuing anyway.")
