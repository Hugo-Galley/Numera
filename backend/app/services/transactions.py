"""Transactions : lecture, filtres et suggestions de virements internes."""
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.transaction import Transaction
from app.repositories import transactions as repo
from app.repositories.transactions import TransactionFilters
from app.services.transfers import candidates_for, find_pairs


def require(db: Session, transaction_id: int) -> Transaction:
    tx = repo.get(db, transaction_id)
    if not tx:
        raise NotFoundError("Transaction not found")
    return tx


def list_merchants(db: Session) -> list[str]:
    return repo.distinct_merchants(db)


def list_transactions(db: Session, filters: TransactionFilters, skip: int, limit: int) -> list[Transaction]:
    return repo.filtered(db, filters, skip, limit)


async def find_potential_transfers(db: Session, days_tolerance: int, amount_tolerance_pct: float, months: int) -> list[dict]:
    """Suggestions de virements internes : une Sortie et une Entree (ou un versement d'investissement)
    de comptes différents, au montant et à la date proches. Appariement 1 pour 1 global : une entrée
    n'est jamais proposée pour deux sorties ; les égalités parfaites sont marquées `ambiguous`."""
    pairs = await find_pairs(
        db,
        day_tolerance=days_tolerance,
        amount_tolerance_pct=amount_tolerance_pct,
        months=months or None,
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
                              account_id: int | None) -> list[dict]:
    """Candidates classées pour relier cette ligne à un virement interne (liaison manuelle)."""
    tx = require(db, transaction_id)
    return await candidates_for(db, tx, days=days, amount_tolerance_pct=amount_tolerance_pct, account_id=account_id)
