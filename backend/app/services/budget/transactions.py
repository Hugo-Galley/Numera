"""Transactions : lecture, filtres et suggestions de virements internes."""
from dataclasses import replace
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.i18n import tr
from app.domain.transactions import category_share
from app.models.transaction import Transaction
from app.repositories.budget import transactions as repo
from app.schemas.transaction_filters import TransactionFilters
from app.services.budget.budget_period import period_bounds
from app.services.budget.transfers import candidates_for, find_pairs


def require(db: Session, transaction_id: int) -> Transaction:
    tx = repo.get(db, transaction_id)
    if not tx:
        raise NotFoundError(tr("errors.transaction_not_found"))
    return tx


def list_merchants(db: Session) -> list[str]:
    return repo.distinct_merchants(db)


def _with_period(db: Session, filters: TransactionFilters) -> TransactionFilters:
    if filters.period and filters.month is not None and filters.year is not None:
        start, end = period_bounds(db, filters.year, filters.month)
        return replace(filters, period_start=start, period_end=end)
    return filters


def list_transactions(db: Session, filters: TransactionFilters, skip: int, limit: int) -> list[Transaction]:
    return repo.filtered(db, _with_period(db, filters), skip, limit)


def total_transactions(db: Session, filters: TransactionFilters) -> dict[str, Any]:
    """Nombre et total net (remboursements déduits) des transactions filtrées, sans limite de page.
    Avec un filtre de catégorie, une dépense découpée ne compte que pour la part de cette catégorie."""
    filters = _with_period(db, filters)
    rows = repo.amounts_filtered(db, filters)
    parts = repo.split_parts(db, [r[0] for r in rows], filters.category_id) if filters.category_id else {}
    total = sum(category_share(amount, offset, parts.get(tx_id)) for tx_id, amount, offset in rows)
    return {"count": len(rows), "total": round(total, 2)}


async def find_potential_transfers(db: Session, days_tolerance: int, amount_tolerance_pct: float, months: int) -> list[dict[str, Any]]:
    """Suggestions de virements internes : une Sortie et une Entree (ou un versement d'investissement)
    de comptes différents, au montant et à la date proches. Appariement 1 pour 1 global : une entrée
    n'est jamais proposée pour deux sorties ; les égalités parfaites sont marquées `ambiguous`."""
    pairs = await find_pairs(
        db,
        day_tolerance=days_tolerance,
        amount_tolerance_pct=amount_tolerance_pct,
        months=months or None,
        light=True,
    )
    return [
        {
            "sortie": p.sortie,
            "entree": p.entree,
            "type": p.kind,
            "confidence": "high" if p.amount_gap_pct < 0.001 and not p.ambiguous else "medium",
            "ambiguous": p.ambiguous,
            "day_gap": p.day_gap,
        }
        for p in pairs
    ]


async def transfer_candidates(db: Session, transaction_id: int, days: int, amount_tolerance_pct: float,
                              account_id: int | None) -> list[dict[str, Any]]:
    """Candidates classées pour relier cette ligne à un virement interne (liaison manuelle)."""
    tx = require(db, transaction_id)
    return await candidates_for(db, tx, days=days, amount_tolerance_pct=amount_tolerance_pct, account_id=account_id)
