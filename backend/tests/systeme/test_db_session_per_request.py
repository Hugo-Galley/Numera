"""Une requête authentifiée n'ouvre qu'une seule session : `get_current_user` et le handler partagent `get_db`."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app


def test_une_seule_session_par_requete_authentifiee(db_session, monkeypatch):
    factory = sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind())
    opened: list[object] = []

    def counting_session_local():
        session = factory()
        opened.append(session)
        return session

    monkeypatch.setattr("app.db.session.SessionLocal", counting_session_local)
    monkeypatch.setattr("app.controllers.deps.SessionLocal", counting_session_local, raising=False)

    token = create_access_token(settings.ADMIN_USERNAME)
    with TestClient(app) as c:
        opened.clear()  # lifespan : migrations/seed ouvrent leurs propres sessions
        response = c.get("/accounts/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert len(opened) == 1


def test_get_db_unique():
    from app.controllers import deps
    from app.db import session

    assert deps.get_db is session.get_db


@pytest.fixture(autouse=True)
def _no_overrides():
    saved = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.update(saved)
