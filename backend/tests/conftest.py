import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["APP_ENV"] = "test"

from app.core.config import settings
from app.core import security
settings.ADMIN_PASSWORD_HASH = security.get_password_hash("admin")

from app.db.base import Base
from app.db.session import get_db as get_db_session
from app.api.deps import get_db as get_db_deps
from app.api.deps import get_current_user
from app.main import app
from app import models # noqa: F401


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
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
