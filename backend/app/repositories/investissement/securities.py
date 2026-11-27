"""Référentiel des titres (`securities`)."""
from collections.abc import Iterable
from typing import Any, cast

from sqlalchemy import Table, func
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.core.time import utcnow_naive
from app.models.security import Security

_OPTIONAL = ("exchange", "country", "sector")


def upsert_many(db: Session, rows: list[dict[str, Any]]) -> None:
    """Insère ou met à jour les titres en une seule instruction groupée (`ON CONFLICT(isin) DO UPDATE`).

    `country`, `sector` et `exchange` ne sont jamais remplacés par NULL, ni `ticker` par un texte vide (SPDR n'en
    publie pas) ; une ligne `source="manual"` n'est pas modifiée.
    Pas de commit : l'appelant valide."""
    if not rows:
        return
    now = utcnow_naive()
    values = [
        {"isin": r["isin"], "ticker": r["ticker"], "name": r["name"], "source": r["source"],
         "updated_at": now, **{k: r.get(k) for k in _OPTIONAL}}
        for r in rows
    ]
    # Table Core (et non l'ORM, qui éclaterait le lot selon les colonnes à NULL) ; `__table__` est typé trop large
    stmt = insert(cast(Table, Security.__table__))
    excluded = stmt.excluded
    stmt = stmt.on_conflict_do_update(
        index_elements=[Security.isin],
        set_={
            "ticker": func.coalesce(func.nullif(excluded.ticker, ""), Security.ticker),
            "name": excluded.name,
            "source": excluded.source,
            "updated_at": excluded.updated_at,
            "exchange": func.coalesce(excluded.exchange, Security.exchange),
            "country": func.coalesce(excluded.country, Security.country),
            "sector": func.coalesce(excluded.sector, Security.sector),
        },
        where=Security.source != "manual",
    )
    db.execute(stmt, values)


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
