"""Profils ETF (`etf_profiles`)."""
from sqlalchemy.orm import Session

from app.models.etf_profile import EtfProfile


def all_profiles(db: Session) -> list[EtfProfile]:
    return db.query(EtfProfile).all()
