"""Référentiel des titres (`securities`)."""
from collections.abc import Iterable
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.core.time import utcnow_naive
from app.models.security import Security

_OPTIONAL = ("exchange", "country", "sector")


def upsert_many(db: Session, rows: list[dict[str, Any]]) -> None:
    """Insère ou met à jour les titres en une seule requête (`ON CONFLICT(isin) DO UPDATE`).

    `country` et `sector` ne sont jamais remplacés par NULL ; une ligne `source="manual"` n'est pas modifiée.
    Pas de commit : l'appelant valide."""
    if not rows:
        return
    now = utcnow_naive()
    values = [
        {"isin": r["isin"], "ticker": r["ticker"], "name": r["name"], "source": r["source"],
         "updated_at": now, **{k: r.get(k) for k in _OPTIONAL}}
        for r in rows
    ]
    stmt = insert(Security).values(values)
    excluded = stmt.excluded
    stmt = stmt.on_conflict_do_update(
        index_elements=[Security.isin],
        set_={
            "ticker": excluded.ticker,
            "name": excluded.name,
            "source": excluded.source,
            "updated_at": excluded.updated_at,
            "exchange": func.coalesce(excluded.exchange, Security.exchange),
            "country": func.coalesce(excluded.country, Security.country),
            "sector": func.coalesce(excluded.sector, Security.sector),
        },
        where=Security.source != "manual",
    )
    db.execute(stmt)


def by_isins(db: Session, isins: Iterable[str]) -> dict[str, Security]:
    wanted = list(set(isins))
    if not wanted:
        return {}
    return {s.isin: s for s in db.query(Security).filter(Security.isin.in_(wanted)).all()}


def by_ticker(db: Session, ticker: str) -> list[Security]:
    """Tous les titres portant ce ticker (une ligne par place de cotation)."""
    return db.query(Security).filter(Security.ticker == ticker).order_by(Security.isin).all()


def by_tickers(db: Session, tickers: Iterable[str]) -> list[Security]:
    """Titres de plusieurs tickers exacts (une requête)."""
    wanted = list(set(tickers))
    if not wanted:
        return []
    return db.query(Security).filter(Security.ticker.in_(wanted)).order_by(Security.isin).all()
