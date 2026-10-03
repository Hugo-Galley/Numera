from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


engine = create_engine(
    settings.database_url, 
    connect_args={"check_same_thread": False, "timeout": 30} if settings.database_url.startswith("sqlite") else {},
    poolclass=NullPool if settings.database_url.startswith("sqlite") else None
)


def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """SQLite ignore les FK (ON DELETE CASCADE / SET NULL) tant que le PRAGMA n'est pas activé,
    et il est propre à chaque connexion."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


if settings.database_url.startswith("sqlite"):
    event.listen(engine, "connect", enable_sqlite_foreign_keys)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
