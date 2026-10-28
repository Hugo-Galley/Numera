"""Paramètres → Sécurité et Données : journal des connexions, déconnexion partout, état des sauvegardes."""
import json
import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.integrations import backup as backup_core
from app.core.config import settings
from app.core.login_events import MAX_EVENTS
from app.db.system_settings import get_setting
from app.models.login_event import LoginEvent


def _login(client, password: str = "admin", agent: str = "Mozilla/5.0 (iPhone) Safari"):
    return client.post(
        "/auth/token",
        data={"username": settings.ADMIN_USERNAME, "password": password},
        headers={"User-Agent": agent, "X-Real-IP": "203.0.113.7"},
    )


def test_login_attempts_are_journaled(client, db_session):
    assert _login(client, "wrong").status_code == 401
    assert _login(client).status_code == 200

    events = client.get("/admin/login-events").json()
    assert [(e["method"], e["success"], e["reason"]) for e in events] == [
        ("password", True, None),
        ("password", False, "invalid_password"),
    ]
    assert events[0]["ip"] == "203.0.113.7"
    assert "iPhone" in events[0]["user_agent"]
    assert db_session.query(LoginEvent).count() == 2


def test_rate_limited_login_is_journaled(client):
    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        _login(client, "wrong")
    assert _login(client, "wrong").status_code == 429
    assert client.get("/admin/login-events?limit=1").json()[0]["reason"] == "rate_limited"


def test_login_journal_keeps_only_recent_events(client, db_session):
    db_session.add_all(LoginEvent(method="password", success=True) for _ in range(MAX_EVENTS + 5))
    db_session.commit()
    _login(client)
    assert db_session.query(LoginEvent).count() == MAX_EVENTS
    latest = db_session.query(LoginEvent).order_by(LoginEvent.id.desc()).first()
    assert latest.ip == "203.0.113.7"


def test_logout_all_invalidates_existing_sessions(client, db_session):
    from fastapi import HTTPException
    from starlette.requests import Request

    from app.controllers import deps
    from app.core import security

    request = Request({"type": "http", "method": "GET", "headers": []})
    before = int(time.time())
    old_token = security.create_access_token(settings.ADMIN_USERNAME, auth_time=before)
    assert deps.get_current_user(request=request, db=db_session, token=old_token) == settings.ADMIN_USERNAME

    assert client.post("/admin/logout-all").json() == {"ok": True}
    assert int(get_setting(db_session, "auth_valid_after")) > before
    # Le jeton émis avant la déconnexion générale est refusé, une nouvelle connexion passe
    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(request=request, db=db_session, token=old_token)
    assert exc.value.status_code == 401
    new_token = security.create_access_token(settings.ADMIN_USERNAME, auth_time=before + 2)
    assert deps.get_current_user(request=request, db=db_session, token=new_token) == settings.ADMIN_USERNAME


def test_privacy_on_start_is_stored_on_profile(client, db_session):
    assert client.get("/admin/profile").json()["privacy_on_start"] is False
    assert client.put("/admin/profile", json={"privacy_on_start": True}).json()["privacy_on_start"] is True
    assert get_setting(db_session, "ui.privacy_on_start") == "true"


def _make_backup(directory, name: str, age: timedelta) -> None:
    path = directory / name
    path.write_bytes(b"x")
    ts = (datetime.now(timezone.utc) - age).timestamp()
    os.utime(path, (ts, ts))


def test_backup_status_without_backups_is_not_configured(client, monkeypatch, tmp_path):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "absent"))
    status = client.get("/admin/backup/status").json()
    assert status["configured"] is False
    assert status["stale"] is False


def test_backup_status_reports_latest_backup(client, monkeypatch, tmp_path):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    monkeypatch.setenv("GITHUB_BACKUP_REPO", "me/backups")
    _make_backup(tmp_path, "suivi_budget_20261020_010000.db.enc", timedelta(days=5))
    _make_backup(tmp_path, "suivi_budget_20261026_010000.db.enc", timedelta(hours=3))
    (tmp_path / "status.json").write_text(json.dumps({
        "last_auto_success_at": "2026-10-26T01:00:00+00:00",
        "github_last_sync_at": "2026-10-26T01:00:05+00:00",
    }))

    status = client.get("/admin/backup/status").json()
    assert status["configured"] is True
    assert status["last_backup_file"] == "suivi_budget_20261026_010000.db.enc"
    assert status["encrypted"] is True
    assert status["backup_count"] == 2
    assert status["github_configured"] is True
    assert status["github_last_sync_at"].startswith("2026-10-26T01:00:05")
    assert status["stale"] is False
    assert status["last_error"] is None


def test_stale_or_failing_backup_raises_an_action(client, monkeypatch, tmp_path):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    _make_backup(tmp_path, "suivi_budget_20261020_010000.db.enc", timedelta(days=4))
    (tmp_path / "status.json").write_text(json.dumps({
        "last_error": "Database not found",
        "last_error_at": datetime.now(timezone.utc).isoformat(),
    }))

    status = backup_core.backup_status()
    assert status["stale"] is True
    assert status["last_error"] == "Database not found"

    actions = client.get("/analytics/actions").json()["actions"]
    backup_actions = [a for a in actions if a["id"].startswith("backup-failing-")]
    assert len(backup_actions) == 1
    assert backup_actions[0]["title"] == "Sauvegarde en retard"
    assert "Database not found" in backup_actions[0]["description"]


def test_old_error_is_hidden_after_a_successful_backup(monkeypatch, tmp_path):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    (tmp_path / "status.json").write_text(json.dumps({
        "last_error": "boom",
        "last_error_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    }))
    _make_backup(tmp_path, "suivi_budget_20261026_010000.db", timedelta(hours=1))
    status = backup_core.backup_status()
    assert status["last_error"] is None
    assert status["encrypted"] is False
    assert status["stale"] is False


def test_no_backup_action_when_backups_are_not_set_up(client, monkeypatch, tmp_path):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "absent"))
    actions = client.get("/analytics/actions").json()["actions"]
    assert not [a for a in actions if a["id"].startswith("backup-failing-")]


def test_backup_script_writes_status(tmp_path):
    import sqlite3
    import subprocess
    import sys
    from pathlib import Path

    db_file = tmp_path / "budget.db"
    sqlite3.connect(db_file).execute("CREATE TABLE t (x INTEGER)").connection.commit()
    backups = tmp_path / "backups"
    script = Path(__file__).resolve().parents[1] / "scripts" / "backup.py"
    env = {
        **os.environ,
        "DB_PATH": str(db_file),
        "BACKUP_DIR": str(backups),
        "BACKUP_KEY": "",
        "APP_ENV": "dev",
        "GITHUB_BACKUP_REPO": "",
        "BACKUP_TRIGGER": "manual",
    }
    result = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    status = json.loads((backups / "status.json").read_text())
    assert status["last_trigger"] == "manual"
    assert status["last_file"].startswith("suivi_budget_")
    assert status["last_error"] is None
    assert "last_auto_success_at" not in status  # une sauvegarde manuelle ne prouve pas que l'automatique tourne

    os.environ["BACKUP_DIR"] = str(backups)
    try:
        assert backup_core.backup_status()["last_backup_file"] == status["last_file"]
    finally:
        del os.environ["BACKUP_DIR"]
