"""Audit R3 : les migrations Alembic doivent produire exactement le schéma des modèles.

Les autres tests utilisent `create_all` et ne voient donc pas les dérives de migration : une
installation neuve ou une restauration sur schéma vierge échouait (colonnes manquantes).
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from app import models  # noqa: F401
from app.db.base import Base

BACKEND = Path(__file__).resolve().parents[1]
PREVIOUS_HEAD = "e3c8a1f5b7d2"  # tête avant la migration de rattrapage


def _alembic(db_url: str, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": db_url, "APP_ENV": "test", "PYTHONPATH": str(BACKEND)}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, capture_output=True, text=True
    )


def _schema_diffs(db_url: str) -> list:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": False, "render_as_batch": True})
        diffs = compare_metadata(ctx, Base.metadata)
    engine.dispose()
    return diffs


def test_upgrade_head_on_empty_database_matches_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    result = _alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    assert _schema_diffs(url) == []


def test_catch_up_is_a_noop_on_a_schema_created_by_create_all(tmp_path):
    """Cas de la prod : base créée par `create_all`, puis marquée à la révision précédente."""
    url = f"sqlite:///{tmp_path / 'prodlike.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO accounts (name, type, currency, active, is_main, created_at, last_verified_at, valuation_mode) "
                          "VALUES ('Courant', 'courant', 'EUR', 1, 0, '2026-01-01', '2026-01-01', 'snapshot')"))
    engine.dispose()

    assert _alembic(url, "stamp", PREVIOUS_HEAD).returncode == 0
    result = _alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    assert _schema_diffs(url) == []
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM accounts")).scalar() == 1
    engine.dispose()


def test_migrated_schema_enforces_cascade_deletes(tmp_path):
    """Avec PRAGMA foreign_keys=ON, supprimer un compte supprime ses transactions."""
    url = f"sqlite:///{tmp_path / 'cascade.db'}"
    assert _alembic(url, "upgrade", "head").returncode == 0
    engine = create_engine(url)
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        conn.execute(text("INSERT INTO accounts (id, name, type, currency, active, is_main, created_at, last_verified_at, valuation_mode) "
                          "VALUES (1, 'A', 'courant', 'EUR', 1, 0, '2026-01-01', '2026-01-01', 'snapshot')"))
        conn.execute(text("INSERT INTO transactions (account_id, date, month_label, type, merchant, amount, currency, original_amount, running_balance) "
                          "VALUES (1, '2026-01-02', 'Janvier', 'Sortie', 'X', 5, 'EUR', 5, 0)"))
        conn.execute(text("DELETE FROM accounts WHERE id = 1"))
        assert conn.execute(text("SELECT COUNT(*) FROM transactions")).scalar() == 0
    engine.dispose()


def test_run_migrations_bootstraps_an_empty_database(tmp_path, monkeypatch):
    """Démarrage sur base vierge : run_migrations produit le schéma exact des modèles."""
    from app.core import migrations
    from app.core.config import settings

    url = f"sqlite:///{tmp_path / 'boot.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setattr(settings, "database_url", url)
    migrations.run_migrations()
    assert _schema_diffs(url) == []
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    engine.dispose()
