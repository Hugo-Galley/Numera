"""Audit R12 : la restauration ne détruit jamais la base existante sur un échec, et le signale."""
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from scripts.restore import restore_backup

BACKEND = Path(__file__).resolve().parents[1]


def _make_db(path: Path, value: int) -> Path:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE t (x INTEGER)")
    con.execute("INSERT INTO t VALUES (?)", (value,))
    con.commit()
    con.close()
    return path


def _value(path: Path) -> int:
    con = sqlite3.connect(path)
    try:
        return con.execute("SELECT x FROM t").fetchone()[0]
    finally:
        con.close()


def test_restore_replaces_database_and_keeps_the_previous_one(tmp_path):
    backup = _make_db(tmp_path / "backup.db", 1)
    dest = _make_db(tmp_path / "live.db", 2)

    assert restore_backup(str(backup), str(dest), None) is True

    assert _value(dest) == 1
    previous = list(tmp_path.glob("live.db.pre-restore-*"))
    assert len(previous) == 1 and _value(previous[0]) == 2
    assert not list(tmp_path.glob("*.tmp"))


def test_corrupt_backup_leaves_destination_untouched(tmp_path):
    backup = tmp_path / "backup.db"
    backup.write_bytes(b"ceci n'est pas une base sqlite" * 50)
    dest = _make_db(tmp_path / "live.db", 2)

    assert restore_backup(str(backup), str(dest), None) is False
    assert _value(dest) == 2
    assert not list(tmp_path.glob("*.tmp"))


def test_wrong_key_leaves_destination_untouched(tmp_path):
    key = Fernet.generate_key().decode()
    plain = _make_db(tmp_path / "plain.db", 1)
    encrypted = tmp_path / "backup.db.enc"
    encrypted.write_bytes(Fernet(key.encode()).encrypt(plain.read_bytes()))
    dest = _make_db(tmp_path / "live.db", 2)

    assert restore_backup(str(encrypted), str(dest), Fernet.generate_key().decode()) is False
    assert _value(dest) == 2
    assert restore_backup(str(encrypted), str(dest), key) is True
    assert _value(dest) == 1


def test_missing_backup_returns_false(tmp_path):
    assert restore_backup(str(tmp_path / "absent.db"), str(tmp_path / "live.db"), None) is False


def test_cli_exits_non_zero_on_failure(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/restore.py", str(tmp_path / "absent.db"), "--dest", str(tmp_path / "live.db")],
        cwd=BACKEND, capture_output=True, text=True,
    )
    assert result.returncode != 0
