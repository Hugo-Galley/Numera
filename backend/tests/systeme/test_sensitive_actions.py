"""Audit R4 : les actions destructrices ou persistantes exigent le mot de passe actuel."""
import sqlite3

import pytest

from app.integrations.backup import snapshot_database
from app.models.account import Account
from app.models.mcp_token import McpToken


@pytest.mark.parametrize("extra", [{}, {"current_password": "mauvais"}])
def test_create_mcp_token_requires_current_password(client, db_session, extra):
    r = client.post("/admin/mcp-tokens", json={"name": "Claude", **extra})
    assert r.status_code == 400
    assert db_session.query(McpToken).count() == 0


def test_create_mcp_token_with_current_password(client, db_session):
    r = client.post("/admin/mcp-tokens", json={"name": "Claude", "current_password": "admin"})
    assert r.status_code == 201
    assert db_session.query(McpToken).count() == 1


@pytest.mark.parametrize("extra", [{}, {"current_password": "mauvais"}])
def test_reset_database_requires_current_password(client, db_session, extra):
    db_session.add(Account(name="Courant", type="courant", currency="EUR", active=True))
    db_session.commit()
    r = client.post(
        "/admin/reset-database", json={"confirm": True, "confirmation_code": "EFFACER", **extra}
    )
    assert r.status_code == 400
    assert db_session.query(Account).count() == 1


def test_snapshot_database_copies_data(tmp_path):
    src = tmp_path / "src.db"
    con = sqlite3.connect(src)
    con.execute("CREATE TABLE t (x INTEGER)")
    con.execute("INSERT INTO t VALUES (42)")
    con.commit()
    con.close()

    dest = snapshot_database(str(src), tmp_path / "backups", prefix="pre-reset")

    assert dest.parent == tmp_path / "backups"
    assert dest.name.startswith("pre-reset_")
    assert sqlite3.connect(dest).execute("SELECT x FROM t").fetchone() == (42,)
