import os
from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

os.environ["APP_ENV"] = "test"

from app.core import security
from app.core.config import settings

settings.ADMIN_PASSWORD_HASH = security.get_password_hash("admin")

from app import models  # noqa: F401
from app.controllers.deps import get_current_user
from app.controllers.deps import get_db as get_db_deps
from app.core.login_rate_limit import login_rate_limiter, totp_rate_limiter
from app.db.base import Base
from app.db.session import enable_sqlite_foreign_keys
from app.db.session import get_db as get_db_session
from app.main import app


def _network_forbidden(*args, **kwargs):
    raise RuntimeError("Réseau interdit en test : patcher l'appel externe")


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Un appel externe non remplacé échoue au lieu de dépendre de la connexion (httpx.MockTransport reste permis)."""
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _network_forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _network_forbidden)


@pytest.fixture(autouse=True)
def fresh_portfolio_cache():
    """Une base de test neuve ne doit jamais lire une valorisation mémorisée par un test précédent."""
    from app.services.investissement.portfolio.cache import invalidate

    invalidate()
    yield
    invalidate()


@pytest.fixture()
def measure_queries(db_session):
    """`measure_queries(appel)` exécute `appel()` et renvoie `(résultat, nombre de requêtes SQL émises)`.

    Garde-fou de performance : borner le nombre de requêtes d'une route ou d'un service sur un jeu de données
    volumineux détecte un N+1 (skill `numera-performance`)."""
    def measure(call):
        statements = []

        def listener(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        engine = db_session.get_bind()
        event.listen(engine, "before_cursor_execute", listener)
        try:
            result = call()
        finally:
            event.remove(engine, "before_cursor_execute", listener)
        return result, len(statements)

    return measure


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    # Même comportement qu'en prod : clés étrangères actives (ON DELETE CASCADE / SET NULL)
    event.listen(engine, "connect", enable_sqlite_foreign_keys)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    login_rate_limiter.clear()
    totp_rate_limiter.clear()
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_get_current_user() -> str:
        return "admin"

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_db_deps] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        login_rate_limiter.clear()
