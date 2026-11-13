"""Filtres de lecture des transactions, partagés par la route, le service et le repository."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TransactionFilters:
    """Filtres de `GET /transactions` (mêmes noms que les paramètres de la route)."""
    account_id: int | None = None
    category_id: int | None = None
    type: str | None = None
    merchant: str | None = None
    month: int | None = None
    year: int | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_transfer: bool | None = None
    tag_ids: list[int] | None = None
    search: str | None = None
    uncategorized: bool = False
    merchant_name: str | None = None
    period: bool = False
    # Bornes du mois de paie, résolues par le service quand `period` est vrai
    period_start: datetime | None = None
    period_end: datetime | None = None
    budget_scope: bool = False
