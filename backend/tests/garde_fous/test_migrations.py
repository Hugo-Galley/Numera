"""Audit R3 : les migrations Alembic doivent produire exactement le schéma des modèles.

Les autres tests utilisent `create_all` et ne voient donc pas les dérives de migration : une
installation neuve ou une restauration sur schéma vierge échouait (colonnes manquantes).
"""
import os
import subprocess
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from app import models  # noqa: F401
from app.db.base import Base

BACKEND = Path(__file__).resolve().parents[2]
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


def test_run_migrations_does_not_need_alembic_on_path(tmp_path, monkeypatch):
    """Venv non activé (CI, `uv sync` sans `source`) : `alembic` absent du PATH ne bloque pas le démarrage."""
    from app.core import migrations
    from app.core.config import settings

    url = f"sqlite:///{tmp_path / 'nopath.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(settings, "database_url", url)
    migrations.run_migrations()
    assert _schema_diffs(url) == []


def test_exchange_rate_uniqueness_migration_removes_duplicates(tmp_path):
    url = f"sqlite:///{tmp_path / 'dups.db'}"
    assert _alembic(url, "upgrade", "a7d3f1c9e5b2").returncode == 0
    engine = create_engine(url)
    with engine.begin() as conn:
        for rate in (1.1, 1.2):
            conn.execute(text("INSERT INTO historical_exchange_rates (date, currency, rate) VALUES ('2026-01-05', 'USD', :r)"), {"r": rate})
    engine.dispose()

    result = _alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT rate FROM historical_exchange_rates")).fetchall() == [(1.1,)]
    engine.dispose()


# Plancher du test de downgrade : `ece5365a3f43` (marchands) ne se rétrograde pas. Son `downgrade` généré
# automatiquement supprime l'index `ix_bank_connections_id` d'une table (`bank_connections`) que ses propres
# migrations ne créent jamais (elle n'existe que sur d'anciennes bases) → `ValueError: No such index`.
# Exception justifiée : on ne réécrit pas une migration ancienne déjà appliquée en production. Les migrations
# antérieures à ce point ne sont donc pas rejouées vers le bas.
DOWNGRADE_FLOOR = "ece5365a3f43"


def test_downgrade_then_upgrade_head_roundtrip(tmp_path):
    """`upgrade head → downgrade <plancher> → upgrade head` sur base vide : toutes les migrations récentes se rejouent.

    Deux migrations de données ont un `downgrade` volontairement vide (7d3f9a21c8b4, f1b7c4a9d2e6) : elles
    corrigent des données existantes, il n'y a rien à défaire sur une base vide. Toute nouvelle migration dont le
    `downgrade` échoue ou laisse un schéma différent des modèles fait échouer ce test ; si l'irréversibilité est
    inévitable, la nommer ici en exception justifiée (comme `DOWNGRADE_FLOOR`), jamais la contourner en silence.
    """
    url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
    assert _alembic(url, "upgrade", "head").returncode == 0
    down = _alembic(url, "downgrade", DOWNGRADE_FLOOR)
    assert down.returncode == 0, down.stderr
    current = _alembic(url, "current")
    assert DOWNGRADE_FLOOR in current.stdout, current.stdout + current.stderr
    up = _alembic(url, "upgrade", "head")
    assert up.returncode == 0, up.stderr
    assert _schema_diffs(url) == []
