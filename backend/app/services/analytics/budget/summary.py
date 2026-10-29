"""Budget du mois : flux (revenus, intérêts, dépenses, investissements), taux d'épargne et patrimoine.

Vue globale : flux convertis en EUR, patrimoine par le calculateur unique `account_values`.
Vue compte (`account_id`) : flux et soldes dans la devise du compte.
"""
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, DomainError, InternalError, NotFoundError
from app.core.logging import get_logger
from app.core.portfolio import positions_values_eur
from app.domain.budget import elapsed_days, savings_rate, to_eur
from app.integrations.currency import get_exchange_rates
from app.models.account import Account
from app.repositories.analytics import budget as repo
from app.repositories.analytics.common import savings_account_ids, savings_events_by_account, ticket_restaurant_account_ids
from app.services.budget_period import period_bounds
from app.services.wealth import account_values, active_accounts

logger = get_logger(__name__)

INVESTMENT_ACCOUNT_TYPES = ("investissement", "assurance_vie")


@dataclass
class _Flows:
    revenus: float
    interets: float
    depenses: float
    real_depenses: float
    investments: float
    remaining: float
    savings_rate: float
    burn_rate: float = 0.0


@dataclass
class _Wealth:
    checking: float = 0.0
    savings: float = 0.0
    investments: float = 0.0
    other: float = 0.0
    solde_actuel: float = 0.0


async def compute_budget(db: Session, month: int | None = None, year: int | None = None,
                         account_id: int | None = None) -> dict:
    if account_id is not None and db.get(Account, account_id) is None:
        raise NotFoundError("Account not found")
    if bool(month) != bool(year):
        raise BusinessRuleError("month et year doivent être fournis ensemble")
    try:
        start = None
        end = datetime.now()
        rates = await get_exchange_rates("EUR")
        if month and year:
            start, end = period_bounds(db, year, month)
        days = _days(db, start, end, bool(month and year))
        is_current_period = end.date() >= date.today()
        if account_id:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise NotFoundError("Account not found")
            wealth = await _account_wealth(db, account, end, rates, is_current_period)
            flows = _account_flows(db, account, start, end, days)
        else:
            flows = _global_flows(db, start, end, rates, days)
            wealth = await _global_wealth(db, end, is_current_period)
        return _response(month, year, flows, wealth, account_id)
    except DomainError:
        raise
    except Exception:
        # Détail volontairement absent de la réponse : il reste dans les logs
        logger.exception("Erreur dans budget_analytics")
        raise InternalError("Erreur interne lors du calcul du budget")


def _days(db: Session, start: datetime | None, end: datetime, monthly: bool) -> int:
    """Jours servant au burn rate : écoulés dans le mois, sinon depuis la première transaction."""
    if monthly:
        return elapsed_days(start, end, datetime.now())
    earliest = repo.earliest_transaction_date(db)
    return max((end - earliest).days, 1) if earliest else 1


def _global_flows(db: Session, start: datetime | None, end: datetime, rates: dict, days: int) -> _Flows:
    """Flux de la vue globale en EUR (courant/épargne hors tickets restaurant, dividendes)."""
    tr_accounts = ticket_restaurant_account_ids(db)
    revenus = to_eur(repo.income_by_currency(db, start, end, tr_accounts), rates)
    revenus += to_eur(repo.dividends_total_by_currency(db, start, end), rates)
    interets = to_eur(repo.interests_by_currency(db, start, end, tr_accounts), rates)
    interets += to_eur(repo.dividends_by_currency(db, start, end), rates)
    depenses = to_eur(repo.expenses_by_currency(db, start, end, tr_accounts), rates)
    # Les dépenses ne contiennent que les sorties catégorisées : on ne retranche
    # que celles-ci, jamais les versements (absents de `depenses`).
    categorized = to_eur(repo.categorized_investments_by_currency(db, start, end, tr_accounts), rates)
    investments = categorized + to_eur(repo.budget_versements_by_currency(db, start, end), rates)
    real_depenses = depenses - categorized
    return _Flows(
        revenus=revenus, interets=interets, depenses=depenses, real_depenses=real_depenses,
        investments=investments, remaining=revenus - depenses,
        savings_rate=savings_rate(revenus, real_depenses), burn_rate=real_depenses / max(days, 1),
    )


def _account_flows(db: Session, account: Account, start: datetime | None, end: datetime, days: int) -> _Flows:
    """Flux d'un compte dans sa devise ; un versement est une entrée, un retrait une dépense."""
    account_id = account.id
    revenus = repo.account_transactions_sum(db, account_id, start, end, ["Entree", "Interets"])
    revenus += repo.account_investment_sum(db, account_id, start, end, "versement")
    depenses = repo.account_transactions_sum(db, account_id, start, end, ["Sortie"])
    depenses += repo.account_investment_sum(db, account_id, start, end, "retrait")
    investments = repo.account_transactions_sum(db, account_id, start, end, ["Sortie"], investment_categories=True)
    investments += repo.account_investment_sum(db, account_id, start, end, "versement")
    # Compte titres : un versement est une entrée du compte, pas une dépense à retrancher
    real_depenses = depenses if account.type in INVESTMENT_ACCOUNT_TYPES else depenses - investments
    return _Flows(
        revenus=revenus,
        interets=repo.account_transactions_sum(db, account_id, start, end, ["Interets"]),
        depenses=depenses, real_depenses=real_depenses, investments=investments, remaining=revenus - depenses,
        # Mêmes formules que la vue globale : taux plafonné, burn rate sur les jours écoulés
        savings_rate=savings_rate(revenus, real_depenses), burn_rate=max(real_depenses, 0.0) / max(days, 1),
    )


async def _global_wealth(db: Session, end: datetime, is_current_period: bool) -> _Wealth:
    """Patrimoine de tous les comptes actifs, tous types, par le calculateur unique."""
    accounts = active_accounts(db)
    # Période en cours : valeur actuelle (positions × cours) ; mois passé : valeur à sa date
    values = await account_values(db, accounts, end if not is_current_period else None)
    account_by_id = {a.id: a for a in accounts}
    wealth = _Wealth(
        investments=sum(v.value_eur for i, v in values.items() if account_by_id[i].type in INVESTMENT_ACCOUNT_TYPES),
        checking=sum(v.value_eur for i, v in values.items() if account_by_id[i].type == "courant"),
        savings=sum(v.value_eur for i, v in values.items() if account_by_id[i].type == "epargne"),
        other=sum(
            v.value_eur
            for i, v in values.items()
            if account_by_id[i].type not in ("courant", "epargne", *INVESTMENT_ACCOUNT_TYPES)
        ),
    )
    wealth.solde_actuel = wealth.checking + wealth.savings + wealth.investments + wealth.other
    return wealth


async def _account_wealth(db: Session, account: Account, end: datetime, rates: dict,
                          is_current_period: bool) -> _Wealth:
    """Valeur d'un compte dans sa devise : titres, solde courant ou épargne selon son type."""
    wealth = _Wealth(investments=await _account_investment_value(db, account, end, rates, is_current_period))
    for row in repo.latest_balance_rows(db, account.id, end):
        if row.type == "courant":
            wealth.checking += row.total
    # Épargne : valeur tenant compte des relevés, pas seulement des transactions
    if account.id in savings_account_ids(db):
        for items in savings_events_by_account(db, [account.id], end).values():
            if items:
                wealth.savings += items[-1][2]
    if account.type in INVESTMENT_ACCOUNT_TYPES:
        wealth.solde_actuel = wealth.investments
    elif account.type == "epargne":
        wealth.solde_actuel = wealth.savings
    else:
        wealth.solde_actuel = wealth.checking
    return wealth


async def _account_investment_value(db: Session, account: Account, end: datetime, rates: dict,
                                    is_current_period: bool) -> float:
    """Compte titres : positions × cours (période en cours), sinon dernier relevé, sinon dernier solde."""
    positions_values = await positions_values_eur(db, [account]) if is_current_period else {}
    if account.type not in INVESTMENT_ACCOUNT_TYPES:
        return 0.0
    if account.id in positions_values:
        return positions_values[account.id] * rates.get(account.currency, 1.0)
    snapshot = repo.latest_snapshot(db, account.id, end)
    if snapshot:
        return float(snapshot.current_value)
    last_tx = repo.last_transaction(db, account.id, end)
    return float(last_tx.running_balance) if last_tx else 0.0


def _response(month: int | None, year: int | None, flows: _Flows, wealth: _Wealth, account_id: int | None) -> dict:
    saved = flows.remaining if account_id else flows.revenus - flows.real_depenses
    return {
        "month": month,
        "year": year,
        "base_currency": "EUR",
        "revenus_totaux": round(float(flows.revenus), 2),
        "interets_totaux": round(float(flows.interets), 2),
        "depenses_totales": round(float(flows.depenses), 2),
        "depenses_reelles": round(float(flows.real_depenses), 2),
        "investissements_du_mois": round(float(flows.investments), 2),
        "revenus_apres_depenses": round(float(flows.remaining), 2),
        # Vue globale : épargné = revenus − dépenses réelles (numérateur du taux d'épargne), dont
        # `reste_tresorerie` = ce qui reste une fois tous les investissements du mois sortis
        "epargne_realisee": round(float(saved), 2),
        "reste_tresorerie": round(float(saved - (0.0 if account_id else flows.investments)), 2),
        "taux_epargne": round(float(flows.savings_rate), 2),
        "burn_rate": round(float(flows.burn_rate), 2),
        "patrimoine_net_total": round(float(wealth.checking + wealth.savings + wealth.investments + wealth.other), 2),
        "epargne_total": round(float(wealth.savings), 2),
        "solde_actuel": round(float(wealth.solde_actuel), 2),
    }
