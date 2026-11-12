"""Lectures de « dernière valeur connue » d'un compte : source unique des repositories (audit A2).

Toutes les bornes `before` sont **exclusives** (règle critique n° 12) ; sans borne, la dernière ligne
du compte. Les versions par lot (`latest_*_by_account`) lisent des colonnes en une requête pour N comptes :
aucun objet ORM, donc aucune relation `selectin` chargée pour lire un solde.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import NamedTuple

from sqlalchemy import ScalarSelect, func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.transaction import Transaction


class SnapshotRow(NamedTuple):
    date: datetime
    current_value: float | None


class BalanceRow(NamedTuple):
    date: datetime
    running_balance: float | None


def active_accounts(db: Session, by_name: bool = False) -> list[Account]:
    """Comptes actifs (tous types), par id ou par nom."""
    query = db.query(Account).filter(Account.active.is_(True))
    return query.order_by(Account.name.asc() if by_name else Account.id.asc()).all()


def latest_snapshot(db: Session, account_id: int, before: datetime | None = None) -> BalanceSnapshot | None:
    """Dernier relevé du compte (strictement avant `before` si donné)."""
    query = db.query(BalanceSnapshot).filter(BalanceSnapshot.account_id == account_id)
    if before is not None:
        query = query.filter(BalanceSnapshot.date < before)
    return query.order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()).first()


def latest_transaction(db: Session, account_id: int, before: datetime | None = None) -> Transaction | None:
    """Dernière transaction du compte (strictement avant `before` si donné)."""
    query = db.query(Transaction).filter(Transaction.account_id == account_id)
    if before is not None:
        query = query.filter(Transaction.date < before)
    return query.order_by(Transaction.date.desc(), Transaction.id.desc()).first()


def _newest_ids(
    db: Session, model: type[Transaction] | type[BalanceSnapshot], ids: list[int], before: datetime | None
) -> ScalarSelect[int]:
    """Sous-requête des ids de la ligne la plus récente de chaque compte (date max, puis id max)."""
    dates_query = db.query(model.account_id.label("account_id"), func.max(model.date).label("max_date")).filter(
        model.account_id.in_(ids)
    )
    if before is not None:
        dates_query = dates_query.filter(model.date < before)
    newest_dates = dates_query.group_by(model.account_id).subquery()
    return (
        db.query(func.max(model.id))
        .join(newest_dates, (model.account_id == newest_dates.c.account_id) & (model.date == newest_dates.c.max_date))
        .group_by(model.account_id)
        .scalar_subquery()
    )


def latest_snapshots_by_account(db: Session, account_ids: Iterable[int], before: datetime | None = None) -> dict[int, SnapshotRow]:
    """Dernier relevé de chacun des comptes, en une requête par colonnes."""
    ids = list(account_ids)
    if not ids:
        return {}
    rows = (
        db.query(BalanceSnapshot.account_id, BalanceSnapshot.date, BalanceSnapshot.current_value)
        .filter(BalanceSnapshot.id.in_(_newest_ids(db, BalanceSnapshot, ids, before)))
        .all()
    )
    return {r.account_id: SnapshotRow(r.date, r.current_value) for r in rows}


def latest_balances_by_account(db: Session, account_ids: Iterable[int], before: datetime | None = None) -> dict[int, BalanceRow]:
    """Dernier solde courant (date, `running_balance`) de chacun des comptes, en une requête par colonnes.

    Max par groupe puis jointure (un passage sur l'index) plutôt qu'une fonction de fenêtre ou une
    sous-requête corrélée, qui classeraient toutes les transactions de chaque compte."""
    ids = list(account_ids)
    if not ids:
        return {}
    rows = (
        db.query(Transaction.account_id, Transaction.date, Transaction.running_balance)
        .filter(Transaction.id.in_(_newest_ids(db, Transaction, ids, before)))
        .all()
    )
    return {r.account_id: BalanceRow(r.date, r.running_balance) for r in rows}
