"""Historique mensuel des KPI (sparklines) : revenus, dépenses, investissements, épargne."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.metrics import kpi_row, savings_at
from app.integrations.currency import get_exchange_rates
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction
from app.repositories.analytics import metrics as repo
from app.repositories.analytics.common import savings_account_ids, savings_events_by_account, ticket_restaurant_account_ids
from app.services.budget_period import current_period, months_back, period_bounds, period_key_expr


def _add(totals: dict[str, float], key: str, amount: float) -> None:
    totals[key] = totals.get(key, 0.0) + amount


async def compute_kpi_history(db: Session, months_count: int = 6, account_id: int | None = None) -> list[dict]:
    now = datetime.now()
    savings_ids = savings_account_ids(db)
    if account_id:
        savings_ids = [account_id] if account_id in savings_ids else []
    savings_accounts = repo.accounts_by_ids(db, savings_ids)
    rates = await get_exchange_rates("EUR")
    tr_accounts = ticket_restaurant_account_ids(db)

    # Pas de transaction : aucun mois à afficher
    if not repo.earliest_transaction_date(db, account_id):
        return []

    history_months = months_back(db, months_count)
    current_ym = current_period(db)
    overall_start = period_bounds(db, *history_months[0])[0]
    overall_end = period_bounds(db, *history_months[-1])[1]
    maps = _monthly_maps(db, overall_start, overall_end, account_id, tr_accounts, rates)
    all_savings_events = savings_events_by_account(db, savings_ids, overall_end) if savings_ids else {}

    results = []
    for y, m in history_months:
        start, end = period_bounds(db, y, m)
        if start > now:  # mois à venir
            continue
        key = f"{y:04d}-{m:02d}"
        rev, dep = maps["rev"].get(key, 0.0), maps["dep"].get(key, 0.0)
        # Ni revenu ni dépense, hors mois en cours : on resserre le graphique
        if rev == 0 and dep == 0 and (y, m) != current_ym:
            continue
        results.append(kpi_row(
            y, m, rev=rev, inte=maps["inte"].get(key, 0.0), dep=dep, inv=maps["inv"].get(key, 0.0),
            cat_inv=maps["cat_inv"].get(key, 0.0),
            epargne=savings_at(all_savings_events, end, savings_accounts, rates),
            account_view=bool(account_id),
        ))
    return results


def _monthly_maps(db: Session, start: datetime, end: datetime, account_id: int | None, tr_accounts: set[int],
                  rates: dict) -> dict[str, dict[str, float]]:
    """Totaux EUR par mois budgétaire : revenus, intérêts, dépenses, investissements, sorties catégorisées investies."""
    maps: dict[str, dict[str, float]] = {name: {} for name in ("rev", "dep", "inte", "inv", "cat_inv")}
    tx_label = period_key_expr(db, Transaction.date, start, end).label("m_label")

    for row in repo.kpi_transaction_rows(db, tx_label, start, end, account_id, tr_accounts):
        amount_eur = row.total / rates.get(row.currency, 1.0)
        if row.type in ("Entree", "Interets"):
            _add(maps["rev"], row.m_label, amount_eur)
        if row.type == "Interets":
            _add(maps["inte"], row.m_label, amount_eur)
        if row.type == "Sortie":
            _add(maps["dep"], row.m_label, amount_eur)

    itx_label = period_key_expr(db, InvestmentTransaction.date, start, end).label("m_label")
    for row in repo.kpi_investment_rows(db, itx_label, start, end, account_id):
        amount_eur = row.total / rates.get(row.currency, 1.0)
        if row.type == "dividende":
            _add(maps["rev"], row.m_label, amount_eur)
            _add(maps["inte"], row.m_label, amount_eur)
        elif row.type == "versement":
            _add(maps["inv"], row.m_label, amount_eur)

    for row in repo.kpi_categorized_investment_rows(db, tx_label, start, end, account_id, tr_accounts):
        amount_eur = row.total / rates.get(row.currency, 1.0)
        _add(maps["inv"], row.m_label, amount_eur)
        _add(maps["cat_inv"], row.m_label, amount_eur)

    for row in repo.kpi_category_interest_rows(db, tx_label, start, end, account_id, tr_accounts):
        _add(maps["inte"], row.m_label, row.total / rates.get(row.currency, 1.0))
    return maps
