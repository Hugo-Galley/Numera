"""Une sauvegarde n'est fiable que si on sait la restaurer : aller-retour réel `backup.py` → `restore.py`.

Contrairement à `test_restore_script.py` (bases jouets), la base est ici migrée par Alembic, en mode WAL,
avec une écriture encore dans le fichier -wal au moment de la sauvegarde ; après restauration le schéma
doit être celui des modèles et les données identiques.
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine

from scripts.restore import restore_backup
from tests.garde_fous.test_migrations import _alembic, _schema_diffs

BACKEND = Path(__file__).resolve().parents[2]


def _live_database(path: Path) -> sqlite3.Connection:
    """Base migrée en WAL ; la connexion reste ouverte pour que les écritures restent dans le -wal."""
    assert _alembic(f"sqlite:///{path}", "upgrade", "head").returncode == 0
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA wal_autocheckpoint=0")
    con.execute("INSERT INTO accounts (id, name, type, currency, active, is_main, created_at, last_verified_at, valuation_mode) "
                "VALUES (1, 'Courant', 'courant', 'EUR', 1, 1, '2026-01-01', '2026-01-01', 'snapshot')")
    con.execute("INSERT INTO transactions (account_id, date, month_label, type, merchant, amount, currency, original_amount, running_balance) "
                "VALUES (1, '2026-01-02', 'Janvier', 'Sortie', 'Boulangerie', 4.5, 'EUR', 4.5, -4.5)")
    con.commit()
    return con


def _run_backup(db: Path, backup_dir: Path, key: str | None) -> Path:
    env = {**os.environ, "DB_PATH": str(db), "BACKUP_DIR": str(backup_dir), "APP_ENV": "test",
           "PYTHONPATH": str(BACKEND), "BACKUP_KEY": key or "", "GITHUB_BACKUP_REPO": "", "GITHUB_BACKUP_TOKEN": ""}
    result = subprocess.run([sys.executable, "scripts/backup.py"], cwd=BACKEND, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    files = list(backup_dir.glob("suivi_budget_*"))
    assert len(files) == 1
    return files[0]


def _snapshot(path: Path) -> dict:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {t: con.execute(f'SELECT * FROM "{t}" ORDER BY 1').fetchall() for t in tables}
    finally:
        con.close()


@pytest.mark.parametrize("encrypted", [False, True], ids=["clair", "chiffre"])
def test_backup_then_restore_gives_back_an_identical_valid_database(tmp_path, encrypted):
    live = tmp_path / "live.db"
    con = _live_database(live)
    assert Path(f"{live}-wal").stat().st_size > 0, "le scénario suppose des écritures encore dans le -wal"
    key = Fernet.generate_key().decode() if encrypted else None

    backup = _run_backup(live, tmp_path / "backups", key)
    assert backup.name.endswith(".enc") == encrypted

    restored = tmp_path / "restored" / "suivi_budget.db"
    assert restore_backup(str(backup), str(restored), key) is True

    assert _snapshot(restored) == _snapshot(live)
    assert _snapshot(restored)["transactions"], "la transaction écrite dans le -wal doit être dans la sauvegarde"
    assert _schema_diffs(f"sqlite:///{restored}") == []
    engine = create_engine(f"sqlite:///{restored}")
    with engine.connect() as c:
        assert c.exec_driver_sql("PRAGMA integrity_check").scalar() == "ok"
    engine.dispose()
    con.close()
