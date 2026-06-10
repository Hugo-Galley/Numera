from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings


def run_migrations() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    alembic_ini = backend_root / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)

    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    )
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())
            alembic_rows = []
            if "alembic_version" in tables:
                try:
                    result = connection.exec_driver_sql("SELECT version_num FROM alembic_version")
                    alembic_rows = result.fetchall()
                except Exception:
                    alembic_rows = []

        if not tables:
            command.upgrade(cfg, "head")
            return

        if "alembic_version" not in tables or not alembic_rows:
            command.stamp(cfg, "head")
            return

        try:
            command.upgrade(cfg, "head")
        except Exception as e:
            error_str = str(e)
            if "Can't locate revision identified by" in error_str:
                print(f"CRITICAL: Database is at an unknown revision ({error_str}). Stamping to current head to attempt recovery.")
                command.stamp(cfg, "head")
                # Try upgrade again in case there were real pending migrations
                try:
                    command.upgrade(cfg, "head")
                except Exception:
                    pass
            else:
                print(f"Migration error: {e}. Attempting to proceed as tables exist.")
    except Exception as e:
        print(f"Error during migration check: {e}")
    finally:
        engine.dispose()
