"""Série annuelle : flux mensuels, points de solde (vue compte) et salaires."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.budget import elapsed_days, to_eur
from app.integrations.currency import get_exchange_rates
from app.repositories.analytics import metrics as repo
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.services.budget.budget_period import period_bounds


async def compute_timeseries(db: Session, year: int, account_id: int | None = None) -> dict:
    now = datetime.now()
    if not repo.has_transaction_in_year(db, year, account_id):
        # Aucune donnée sur l'année : séries vides plutôt que douze zéros
        return {"year": year, "account_id": account_id, "monthly_flows": [], "balance_points": [], "salary_series": []}

    rates = await get_exchange_rates("EUR")
    tr_accounts = ticket_restaurant_account_ids(db)
    monthly = []
    for month in range(1, 13):
        start, end = period_bounds(db, year, month)
        if start > now:  # mois à venir
            continue
        income, expense = _month_flows(db, start, end, account_id, tr_accounts, rates)
        # Mois retenu s'il a des flux, ou s'il est en cours
        if income > 0 or expense > 0 or start <= now < end:
            days = elapsed_days(start, end, now)
            monthly.append({
                "month": month,
                "income": round(float(income), 2),
                "expense": round(float(expense), 2),
                "burn_rate": round(float(expense) / max(days, 1), 2),
            })

    # Vue globale : des soldes de comptes entremêlés n'ont pas de sens, pas de points
    balance_points = [
        {"date": tx.date.isoformat(), "running_balance": round(float(tx.running_balance), 2), "account_id": tx.account_id}
        for tx in repo.account_transactions(db, account_id)
    ] if account_id is not None else []

    return {
        "year": year,
        "account_id": account_id,
        "monthly_flows": monthly,
        "balance_points": balance_points,
        "salary_series": _salary_series(db, year, account_id, rates, now),
    }


def _month_flows(db: Session, start: datetime, end: datetime, account_id: int | None, tr_accounts: set[int],
                 rates: dict) -> tuple[float, float]:
    """Revenus (dividendes compris) et dépenses du mois en EUR ; un compte titres compte ses versements en dépenses."""
    income = to_eur(repo.month_income_rows(db, start, end, account_id, tr_accounts), rates)
    income += to_eur(repo.month_investment_rows(db, start, end, "dividende", account_id), rates)
    expense = to_eur(repo.month_expense_rows(db, start, end, account_id, tr_accounts), rates)
    if account_id:
        account = repo.get_account(db, account_id)
        if account and account.type == "investissement":
            expense += to_eur(repo.month_investment_rows(db, start, end, "versement", account_id), rates)
    return income, expense


def _salary_series(db: Session, year: int, account_id: int | None, rates: dict, now: datetime) -> list[dict]:
    salary_by_month: dict[int, float] = {}
    for month in range(1, 13):
        m_start, m_end = period_bounds(db, year, month)
        total = to_eur(repo.salary_rows(db, m_start, m_end, account_id), rates)
        if total:
            salary_by_month[month] = total
    return [
        {"month": month, "salary": salary_by_month.get(month, 0.0)}
        for month in range(1, 13)
        # Mois passés ou en cours ayant un salaire
        if period_bounds(db, year, month)[0] <= now and (salary_by_month.get(month, 0) > 0)
    ]
