import subprocess
import sys
import os
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


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

        # 2. Run alembic upgrade head
        env = {**os.environ, "PYTHONPATH": str(backend_root)}
        logger.info(f"Executing: alembic upgrade head in {backend_root}")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=str(backend_root),
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode == 0:
            logger.info("Migrations successful:\n" + result.stdout)
        else:
            logger.error(f"Migrations failed (exit {result.returncode}):\n" + result.stderr)
            
            # Fallback: if it's a revision error, try stamping
            if "Can't locate revision identified by" in result.stderr:
                logger.warning("Unknown revision detected. Attempting 'alembic stamp head'...")
                subprocess.run(["alembic", "stamp", "head"], cwd=str(backend_root), env=env)
                subprocess.run(["alembic", "upgrade", "head"], cwd=str(backend_root), env=env)
                
    except Exception as e:
        logger.error(f"Unexpected error during migration subprocess: {e}", exc_info=True)


