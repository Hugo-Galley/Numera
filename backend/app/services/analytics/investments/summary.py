"""Vue d'ensemble des investissements (`/investments`) : capital net investi, valeur et gain par compte."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.investissement.holdings.replay import replay_account
from app.domain.portfolio import uses_positions
from app.services.investissement.portfolio import compute_portfolio
from app.integrations.currency import get_exchange_rates
from app.models.account import Account
from app.repositories.analytics import investments as repo
from app.services.analytics.investments.flows import calculate_investment_flows
from app.services.budget.budget_period import period_bounds


async def compute_investments(db: Session, month: int | None = None, year: int | None = None,
                              account_id: int | None = None) -> dict:
    # Un compte qui n'est pas d'investissement est ignoré : vue d'ensemble du dashboard
    target_account = repo.get_account(db, account_id) if account_id else None
    scoped = target_account is not None and target_account.type in repo.INVESTMENT_TYPES
    accounts = repo.investment_accounts(db, account_id if scoped else None)
    rates = await get_exchange_rates("EUR")
    start_date = None
    end_date = datetime.now()
    if month and year:
        # Fenêtre du mois budgétaire (mois de paie en mode « salaire »), comme les autres KPI mensuels
        start_date, end_date = period_bounds(db, year, month)
    latest_values, latest_dates = _latest_values(db, accounts, end_date)

    totals = {"net_invested": 0.0, "current_value": 0.0, "gain": 0.0, "gain_base": 0.0}
    items = []
    for account in accounts:
        # Sur toute la période, un compte titres est valorisé par ses positions × cours (les relevés ne servent qu'au rapprochement)
        if start_date is None and uses_positions(account, await replay_account(db, account.id)):
            items.append(await _positions_item(db, account, totals))
            continue
        flows = await calculate_investment_flows(db, account, end_date, start_date=start_date, target_currency="EUR")
        items.append(_snapshot_item(account, flows, latest_values.get(account.id), latest_dates.get(account.id),
                                    start_date, rates, totals))

    # Le gain total ne compte que les comptes évaluables (un compte sans valeur récente n'est pas une perte)
    total_performance_pct = (totals["gain"] / totals["gain_base"] * 100.0) if totals["gain_base"] > 0 else 0.0
    return {
        "total_net_invested": round(totals["net_invested"], 2),
        "total_current_value": round(totals["current_value"], 2),
        "total_gain_eur": round(totals["gain"], 2),
        "total_performance_pct": round(total_performance_pct, 2),
        "items": items,
    }


def _latest_values(db: Session, accounts: list[Account], end_date: datetime) -> tuple[dict, dict]:
    """Dernière valeur connue de chaque compte à `end_date` : relevé, sinon dernier solde courant."""
    rows = repo.latest_snapshot_rows(db, end_date)
    values = {row.account_id: float(row.current_value or 0.0) for row in rows}
    dates = {row.account_id: row.date for row in rows}
    for acc in accounts:
        if acc.id not in values:
            last_tx = repo.last_transaction(db, acc.id, until=end_date)
            if last_tx:
                values[acc.id] = float(last_tx.running_balance)
                dates[acc.id] = last_tx.date
    return values, dates


async def _positions_item(db: Session, account: Account, totals: dict) -> dict:
    p = await compute_portfolio(db, account, history=False)
    totals["net_invested"] += p["net_invested_eur"]
    totals["current_value"] += p["value_eur"]
    if p["performance_pct"] is not None:
        totals["gain"] += p["gain_eur"]
        totals["gain_base"] += p["net_invested_eur"]
    return {
        "account_id": account.id,
        "account_name": account.name,
        "total_verse": round(p["net_invested"], 2),
        "total_retire": 0.0,
        "net_invested": p["net_invested_eur"],
        "current_value": p["value_eur"],
        "gain_eur": p["gain_eur"],
        "performance_pct": p["performance_pct"] or 0.0,
        "currency": account.currency,
        "value_source": "positions",
        "value_stale": False,
        "xirr_pct": p["xirr_pct"],
        "unrealized_eur": p["unrealized_eur"],
        "realized_eur": p["realized_eur"],
        "dividends_eur": p["dividends_eur"],
    }


def _snapshot_item(account: Account, flows: dict, raw_current_value: float | None, value_date: datetime | None,
                   start_date: datetime | None, rates: dict, totals: dict) -> dict:
    net_invested_eur = flows["net_invested_target"]
    current_value_eur = raw_current_value / rates.get(account.currency, 1.0) if raw_current_value is not None else 0.0
    # Sur un mois, le gain n'a de sens que si la valeur est postérieure au dernier flux de la période :
    # un relevé plus ancien que le versement ferait passer ce versement pour une perte.
    last_flow = flows.get("last_flow_date")
    value_stale = raw_current_value is None or (
        start_date is not None and last_flow is not None and (value_date is None or value_date < last_flow)
    )
    if value_stale:
        gain_eur = performance_pct = None
    else:
        gain_eur = current_value_eur - net_invested_eur
        performance_pct = (gain_eur / net_invested_eur * 100.0) if net_invested_eur > 0 else 0.0
        totals["gain"] += gain_eur
        totals["gain_base"] += max(net_invested_eur, 0.0)
    totals["net_invested"] += net_invested_eur
    totals["current_value"] += current_value_eur
    return {
        "account_id": account.id,
        "account_name": account.name,
        "total_verse": round(flows["total_verse_target"], 2),
        "total_retire": round(flows["total_retire_target"], 2),
        "net_invested": round(net_invested_eur, 2),
        "current_value": round(current_value_eur, 2),
        "gain_eur": round(gain_eur, 2) if gain_eur is not None else None,
        "performance_pct": round(performance_pct, 2) if performance_pct is not None else None,
        "currency": account.currency,
        "value_source": "snapshot" if raw_current_value is not None else "none",
        "value_stale": value_stale,
    }
