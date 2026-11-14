"""Chemins de `services/systeme/admin.py` restés sans test : profil, remise à zéro, délai de sauvegarde."""
import subprocess

from sqlalchemy.orm import sessionmaker

from app.core import security
from app.db.base import Base
from app.db.system_settings import get_setting
from app.models.account import Account
from app.models.category import Category
from app.services.systeme import admin

RESET = {"confirm": True, "confirmation_code": "EFFACER", "current_password": "admin"}


def test_password_too_short_is_refused_and_hash_unchanged(client, db_session):
    r = client.put("/admin/profile", json={"password": "court", "current_password": "admin"})

    assert r.status_code == 422
    assert not get_setting(db_session, "admin_password_hash")


def test_new_password_is_stored_hashed(client, db_session):
    r = client.put("/admin/profile", json={"password": "nouveau-mot-de-passe", "current_password": "admin"})

    assert r.status_code == 200
    stored = get_setting(db_session, "admin_password_hash")
    assert security.verify_password("nouveau-mot-de-passe", stored)


def test_profile_picture_is_stored(client, db_session):
    r = client.put("/admin/profile", json={"profile_picture_url": "https://example.org/moi.png"})

    assert r.status_code == 200
    assert r.json()["profile_picture_url"] == "https://example.org/moi.png"
    assert get_setting(db_session, "profile_picture_url") == "https://example.org/moi.png"


def test_reset_requires_confirmation_and_code(client, db_session):
    db_session.add(Account(name="Courant", type="courant", currency="EUR", active=True))
    db_session.commit()

    assert client.post("/admin/reset-database", json={**RESET, "confirm": False}).status_code == 400
    assert client.post("/admin/reset-database", json={**RESET, "confirmation_code": "effacer"}).status_code == 400
    assert db_session.query(Account).count() == 1


def _use_test_database(monkeypatch, db_session):
    """Le service agit sur le moteur global : on le remplace par celui de la base temporaire du test."""
    engine = db_session.get_bind()
    monkeypatch.setattr(admin, "engine", engine)
    monkeypatch.setattr(admin, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(admin, "run_migrations", lambda: Base.metadata.create_all(bind=engine))
    return engine


def test_reset_wipes_data_reseeds_categories_and_keeps_a_snapshot(client, db_session, monkeypatch, tmp_path):
    _use_test_database(monkeypatch, db_session)
    db_session.add(Account(name="Courant", type="courant", currency="EUR", active=True))
    db_session.commit()

    r = client.post("/admin/reset-database", json=RESET)

    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    db_session.expire_all()
    assert db_session.query(Account).count() == 0
    assert db_session.query(Category).count() > 0
    # Filet de sécurité : l'état d'avant est copié à côté de la base
    snapshots = list((tmp_path / "backups").glob("pre-reset_*.db"))
    assert len(snapshots) == 1


def test_reset_is_cancelled_when_the_snapshot_fails(client, db_session, monkeypatch):
    _use_test_database(monkeypatch, db_session)
    db_session.add(Account(name="Courant", type="courant", currency="EUR", active=True))
    db_session.commit()

    def broken_snapshot(*args, **kwargs):
        raise OSError("disque plein")

    monkeypatch.setattr(admin, "snapshot_database", broken_snapshot)

    r = client.post("/admin/reset-database", json=RESET)

    assert r.status_code == 500
    assert db_session.query(Account).count() == 1


def test_manual_backup_timeout_is_a_504(client, monkeypatch):
    def too_slow(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(admin.subprocess, "run", too_slow)

    assert client.post("/admin/backup/run").status_code == 504
