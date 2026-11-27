"""Profils ETF (`etf_profiles`)."""
from sqlalchemy import update
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
    """Le profil système d'abord : un profil de référence peut porter le nom d'un indice."""
    return db.query(EtfProfile).filter(EtfProfile.name == name).order_by(EtfProfile.is_system.desc()).first()


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


def get_many(db: Session, ids: set[int]) -> list[EtfProfile]:
    if not ids:
        return []
    return db.query(EtfProfile).filter(EtfProfile.id.in_(ids)).order_by(EtfProfile.name).all()


def find_by_isin(db: Session, isin: str) -> EtfProfile | None:
    return db.query(EtfProfile).filter(EtfProfile.isin == isin).order_by(EtfProfile.id).first()


def attach_to_holdings(db: Session, sym: str, profile_id: int) -> None:
    """Rattache au profil les positions de même ticker qui n'en ont pas."""
    db.query(PortfolioHolding).filter(
        PortfolioHolding.ticker.ilike(sym),
        PortfolioHolding.etf_profile_id.is_(None)
    ).update({"etf_profile_id": profile_id}, synchronize_session=False)


def add(db: Session, profile: EtfProfile) -> None:
    db.add(profile)


def flush(db: Session) -> None:
    db.flush()


def delete(db: Session, profile: EtfProfile) -> None:
    db.delete(profile)


def identities(db: Session) -> list[tuple[int, str, str | None, str | None]]:
    """(id, ticker, alias JSON, ISIN) de tous les profils, sans objets ORM."""
    return [(i, t, a, s) for i, t, a, s in db.query(EtfProfile.id, EtfProfile.ticker, EtfProfile.aliases, EtfProfile.isin)]


def holding_isins(db: Session) -> list[tuple[int, str, str | None]]:
    """(profil, ticker, ISIN) des positions rattachées à un profil et dotées d'un ISIN."""
    rows = db.query(PortfolioHolding.etf_profile_id, PortfolioHolding.ticker, PortfolioHolding.isin).filter(
        PortfolioHolding.etf_profile_id.isnot(None), PortfolioHolding.isin.isnot(None), PortfolioHolding.isin != "")
    return [(p, t, i) for p, t, i in rows.distinct() if p is not None]


def set_isins(db: Session, isins: dict[int, str]) -> None:
    """Un ISIN par profil, en une instruction ; le profil sera relu au prochain passage (pas de commit)."""
    if isins:
        db.execute(update(EtfProfile), [
            {"id": pid, "isin": isin, "composition_refreshed_at": None} for pid, isin in isins.items()])
