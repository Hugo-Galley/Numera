"""Profils ETF (`etf_profiles`)."""
from sqlalchemy.orm import Session

from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding


def all_profiles(db: Session) -> list[EtfProfile]:
    return db.query(EtfProfile).all()


def list_ordered(db: Session) -> list[EtfProfile]:
    """Profils système d'abord, puis par nom."""
    return db.query(EtfProfile).order_by(EtfProfile.is_system.desc(), EtfProfile.name.asc()).all()


def get(db: Session, profile_id: int) -> EtfProfile | None:
    return db.query(EtfProfile).filter(EtfProfile.id == profile_id).first()


def find_by_ticker_or_name(db: Session, ticker: str, name: str) -> EtfProfile | None:
    return db.query(EtfProfile).filter((EtfProfile.ticker == ticker) | (EtfProfile.name == name)).first()


def find_by_symbol_or_alias(db: Session, sym: str) -> EtfProfile | None:
    return db.query(EtfProfile).filter(
        (EtfProfile.ticker.ilike(sym)) |
        (EtfProfile.aliases.ilike(f'%"{sym}"%'))
    ).first()


def find_by_name(db: Session, name: str) -> EtfProfile | None:
    return db.query(EtfProfile).filter(EtfProfile.name == name).first()


def held_profiles(db: Session) -> list[EtfProfile]:
    """Profils rattachés à une position détenue."""
    ids = {
        pid for (pid,) in db.query(PortfolioHolding.etf_profile_id)
        .filter(PortfolioHolding.etf_profile_id.isnot(None), PortfolioHolding.quantity > 0)
        .distinct()
    }
    if not ids:
        return []
    return db.query(EtfProfile).filter(EtfProfile.id.in_(ids)).order_by(EtfProfile.name).all()


def attach_to_holdings(db: Session, sym: str, profile_id: int) -> None:
    """Rattache au profil les positions de même ticker qui n'en ont pas."""
    db.query(PortfolioHolding).filter(
        PortfolioHolding.ticker.ilike(sym),
        PortfolioHolding.etf_profile_id.is_(None)
    ).update({"etf_profile_id": profile_id}, synchronize_session=False)


def add(db: Session, profile: EtfProfile) -> None:
    db.add(profile)


def delete(db: Session, profile: EtfProfile) -> None:
    db.delete(profile)
