"""`execute_read_query` : tables sensibles illisibles et durée bornée, même avec un SELECT valide.

Lancer : cd mcp-server && uv run --with pytest python -m pytest test_server_sqlite_query.py -q
"""
import sqlite3

import pytest

import server_sqlite


@pytest.fixture()
def db_file(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE system_settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO system_settings VALUES ('mcp_enabled', 'true'), ('admin_password_hash', 'HASH-SECRET');
        CREATE TABLE mcp_tokens (id INTEGER PRIMARY KEY, token_hash TEXT);
        INSERT INTO mcp_tokens VALUES (1, 'TOKEN-SECRET');
        CREATE TABLE login_events (id INTEGER PRIMARY KEY, ip TEXT);
        INSERT INTO login_events VALUES (1, '203.0.113.9');
        CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO accounts VALUES (1, 'Courant');
        """
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(server_sqlite, "DB_PATH", str(path))
    return path


def test_regular_table_is_readable(db_file):
    assert "Courant" in server_sqlite.execute_read_query("SELECT * FROM accounts")


@pytest.mark.parametrize("sql", [
    "SELECT * FROM system_settings",
    "SELECT value FROM system_settings WHERE key = 'admin_password_hash'",
    "SELECT * FROM mcp_tokens",
    "SELECT * FROM login_events",
    "SELECT name FROM accounts WHERE id IN (SELECT id FROM mcp_tokens)",
    "SELECT a.name FROM accounts a JOIN system_settings s ON 1=1",
])
def test_sensitive_tables_are_refused(db_file, sql):
    result = server_sqlite.execute_read_query(sql)
    assert "SECRET" not in result and "203.0.113.9" not in result
    assert result.startswith("❌")


def test_runaway_query_is_interrupted(db_file, monkeypatch):
    monkeypatch.setattr(server_sqlite, "QUERY_TIMEOUT_S", 0.2)
    sql = (
        "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c WHERE x < 100000000000) "
        "SELECT count(*) FROM c LIMIT 1"
    )
    assert server_sqlite.execute_read_query(sql).startswith("❌")
