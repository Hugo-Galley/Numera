"""Référentiel des titres (`securities`)."""
from collections.abc import Iterable
from typing import Any, cast

from sqlalchemy import ColumnElement, Table, and_, case, func, or_
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.core.time import utcnow_naive
from app.models.security import Security

_OPTIONAL = ("exchange", "country", "sector")


def upsert_many(db: Session, rows: list[dict[str, Any]]) -> None:
    """Insère ou met à jour les titres en une seule instruction groupée (`ON CONFLICT(isin) DO UPDATE`).

    `country`, `sector` et `exchange` ne sont jamais remplacés par NULL, ni `ticker` par un texte vide (SPDR n'en
    publie pas) ; une ligne `source="manual"` garde tous ses champs ; sans pays ni secteur, seule sa date `updated_at` avance.
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
    manual = Security.source == "manual"

    def unless_manual(new: Any, current: Any) -> ColumnElement[Any]:
        return case((manual, current), else_=new)

    stmt = stmt.on_conflict_do_update(
        index_elements=[Security.isin],
        set_={
            "ticker": unless_manual(func.coalesce(func.nullif(excluded.ticker, ""), Security.ticker), Security.ticker),
            "name": unless_manual(excluded.name, Security.name),
            "source": unless_manual(excluded.source, Security.source),
            "updated_at": excluded.updated_at,
            "exchange": unless_manual(func.coalesce(excluded.exchange, Security.exchange), Security.exchange),
            "country": unless_manual(func.coalesce(excluded.country, Security.country), Security.country),
            "sector": unless_manual(func.coalesce(excluded.sector, Security.sector), Security.sector),
        },
        # Une ligne saisie sans pays ni secteur ne garde que la date d'interrogation : sans elle, Yahoo serait
        # redemandé à chaque scan (`_needs_yahoo`)
        where=or_(~manual, and_(Security.country.is_(None), Security.sector.is_(None))),
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
