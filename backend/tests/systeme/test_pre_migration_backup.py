"""Audit M3 : une mise à jour qui change le schéma sauvegarde la base AVANT d'appliquer les migrations."""
import sqlite3

import pytest
from cryptography.fernet import Fernet

from app.core import migrations
from app.core.config import settings
from tests.garde_fous.test_migrations import PREVIOUS_HEAD, _alembic


@pytest.fixture
def env(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    backups = tmp_path / "backups"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("BACKUP_DIR", str(backups))
    monkeypatch.delenv("BACKUP_KEY", raising=False)
    monkeypatch.setattr(settings, "database_url", url)
    return url, tmp_path / "app.db", backups


def _old_database(url: str, path) -> None:
    assert _alembic(url, "upgrade", PREVIOUS_HEAD).returncode == 0
    con = sqlite3.connect(path)
    con.execute("INSERT INTO accounts (id, name, type, currency, active, is_main, created_at, last_verified_at, valuation_mode) "
                "VALUES (1, 'Courant', 'courant', 'EUR', 1, 1, '2026-01-01', '2026-01-01', 'snapshot')")
    con.commit()
    con.close()


def test_outdated_schema_is_backed_up_before_upgrade(env):
    url, path, backups = env
    _old_database(url, path)
    migrations.run_migrations()
    files = list(backups.glob("pre_migration_*"))
    assert len(files) == 1
    assert PREVIOUS_HEAD in files[0].name
    copy = sqlite3.connect(files[0])
    assert copy.execute("SELECT version_num FROM alembic_version").fetchone()[0] == PREVIOUS_HEAD
    assert copy.execute("SELECT name FROM accounts").fetchall() == [("Courant",)]
    copy.close()


def test_up_to_date_schema_is_not_backed_up(env):
    _, _, backups = env
    migrations.run_migrations()  # base vierge : rien à protéger
    assert not list(backups.glob("pre_migration_*"))
    migrations.run_migrations()  # déjà à jour
    assert not list(backups.glob("pre_migration_*"))


def test_pre_migration_backup_is_encrypted_when_key_is_set(env, monkeypatch):
    url, path, backups = env
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("BACKUP_KEY", key)
    _old_database(url, path)
    migrations.run_migrations()
    (enc,) = backups.glob("pre_migration_*.db.enc")
    plain = Fernet(key.encode()).decrypt(enc.read_bytes())
    assert plain.startswith(b"SQLite format 3")
    assert not list(backups.glob("pre_migration_*.db"))


def test_pre_migration_backups_are_bounded(env):
    url, path, backups = env
    backups.mkdir()
    for i in range(8):
        (backups / f"pre_migration_old_2026010{i + 1}_000000.db").write_bytes(b"x")
    _old_database(url, path)
    migrations.run_migrations()
    files = sorted(p.name for p in backups.glob("pre_migration_*"))
    assert len(files) == migrations.PRE_MIGRATION_KEEP
    assert any(PREVIOUS_HEAD in name for name in files)  # la nouvelle sauvegarde est conservée
