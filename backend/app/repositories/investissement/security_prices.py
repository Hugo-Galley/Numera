"""Cours de clôture stockés (`security_prices`) et titres détenus à coter."""
from datetime import date as date_type

from sqlalchemy.orm import Session

from app.models.portfolio_holding import PortfolioHolding
from app.models.security_price import SecurityPrice


def store_price(db: Session, ticker: str, day: date_type, close: float, currency: str, source: str = "yahoo") -> None:
    """Enregistre (ou met à jour) le cours de clôture d'un titre pour un jour donné. Ne commit pas."""
    sym = ticker.upper().strip()
    row = db.query(SecurityPrice).filter(SecurityPrice.ticker == sym, SecurityPrice.date == day).first()
    if row is None:
        db.add(SecurityPrice(ticker=sym, date=day, close=close, currency=currency, source=source))
    else:
        row.close, row.currency, row.source = close, currency, source


def latest(db: Session, ticker: str, on_or_before: date_type | None = None) -> SecurityPrice | None:
    q = db.query(SecurityPrice).filter(SecurityPrice.ticker == ticker.upper().strip())
    if on_or_before is not None:
        q = q.filter(SecurityPrice.date <= on_or_before)
    return q.order_by(SecurityPrice.date.desc()).first()


def latest_demo(db: Session, sym: str) -> SecurityPrice | None:
    """Dernier cours généré par le jeu de démonstration (`source == "demo"`)."""
    return (
        db.query(SecurityPrice)
        .filter(SecurityPrice.ticker == sym, SecurityPrice.source == "demo")
        .order_by(SecurityPrice.date.desc())
        .first()
    )


def series_by_ticker(db: Session, tickers: list[str]) -> dict[str, list[tuple[date_type, float, str]]]:
    """Cours (date, clôture, devise) de chaque titre demandé, par date croissante, en une requête ; un titre sans
    cours a une liste vide."""
    out: dict[str, list[tuple[date_type, float, str]]] = {ticker: [] for ticker in tickers}
    if not tickers:
        return out
    rows = (
        db.query(SecurityPrice.ticker, SecurityPrice.date, SecurityPrice.close, SecurityPrice.currency)
        .filter(SecurityPrice.ticker.in_(set(tickers)))
        .order_by(SecurityPrice.ticker, SecurityPrice.date.asc())
        .all()
    )
    for ticker, day, close, currency in rows:
        out[ticker].append((day, close, currency))
    return out


def held_tickers(db: Session) -> list[str]:
    """Tickers des positions non soldées, triés."""
    return sorted({t for (t,) in db.query(PortfolioHolding.ticker).filter(PortfolioHolding.quantity > 0).distinct()})
