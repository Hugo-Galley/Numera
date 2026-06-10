from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.migrations import run_migrations
from app.core.seeds import seed_default_categories
from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db

router = APIRouter(prefix="/admin", tags=["admin"])


class ResetDatabaseRequest(BaseModel):
    confirm: bool = False
    confirmation_code: str | None = None


@router.post("/reset-database")
def reset_database(payload: ResetDatabaseRequest, db: Session = Depends(get_db)):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    
    if payload.confirmation_code != "EFFACER":
        raise HTTPException(status_code=400, detail="Invalid confirmation code. Please type 'EFFACER' to confirm.")

    db.close()

    Base.metadata.drop_all(bind=engine)
    with engine.connect() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        connection.commit()

    run_migrations()
    seed_db = SessionLocal()
    try:
        seed_default_categories(seed_db)
    finally:
        seed_db.close()

    return {"status": "ok"}
