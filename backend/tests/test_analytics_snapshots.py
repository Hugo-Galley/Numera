"""Instantanés (« golden master ») de toutes les routes analytics, sur les données de démo à date figée.

Filet de sécurité de la migration en couches : un déplacement de code ne doit changer aucun chiffre.
Ne jamais régénérer pour faire passer le test : un écart est un bug. Régénération volontaire :
`UPDATE_SNAPSHOTS=1 PYTHONPATH=. python3.11 -m pytest tests/test_analytics_snapshots.py`.
"""
import asyncio
import json
import os
import random
from datetime import date, datetime
from pathlib import Path

import pytest
from freezegun import freeze_time

import app.integrations.yahoo_finance as yahoo_finance
import app.services.investissement.market.quotes as market_quotes
import app.integrations.currency as currency_mod
from app.services.systeme.demo import generate_demo_data
from app.models.account import Account
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.reimbursement import ReimbursementClaim
from app.models.salary_config import SalaryConfig
from app.models.transaction import Transaction
from app.services.balances import recalculate_running_balances

SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "analytics"
FROZEN_NOW = "2026-06-15 10:00:00"
TODAY = date(2026, 6, 15)
MONTHS = [(5, 2026), (6, 2026)]
SIM = {"initial_capital": 10000, "monthly_contribution": 500, "annual_return_pct": 6}
EVENTS = json.dumps([{"year": 3, "amount": -15000, "label": "Voiture"}])


def _normalize(obj):
    """Arrondit les flottants à 6 décimales et trie les clés ; l'ordre des listes fait partie du contrat."""
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, dict):
        return {k: _normalize(obj[k]) for k in sorted(obj)}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    return obj


def _first_diff(expected, actual, path="$"):
    if type(expected) is not type(actual):
        return f"{path}: {expected!r} != {actual!r}"
    if isinstance(expected, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in expected or key not in actual:
                return f"{path}.{key}: clé {'absente' if key not in actual else 'en trop'}"
            diff = _first_diff(expected[key], actual[key], f"{path}.{key}")
            if diff:
                return diff
        return None
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return f"{path}: longueur {len(expected)} != {len(actual)}"
        for i, (e, a) in enumerate(zip(expected, actual)):
            diff = _first_diff(e, a, f"{path}[{i}]")
            if diff:
                return diff
        return None
    return None if expected == actual else f"{path}: {expected!r} != {actual!r}"


def _month_routes(name: str, path: str, extra: dict | None = None) -> list[tuple[str, str, dict]]:
    return [(f"{name}_{y}_{m:02d}", path, {"month": m, "year": y, **(extra or {})}) for m, y in MONTHS]


def _routes(accounts: dict[str, int]) -> list[tuple[str, str, dict]]:
    courant = accounts["courant"]
    routes: list[tuple[str, str, dict]] = [
        *_month_routes("budget", "/analytics/budget"),
        *_month_routes("budget_courant", "/analytics/budget", {"account_id": courant}),
        ("budget_default", "/analytics/budget", {}),
        *_month_routes("resilience", "/analytics/resilience"),
        *_month_routes("budget_alerts", "/analytics/budget-alerts"),
        *_month_routes("budget_alerts_courant", "/analytics/budget-alerts", {"account_id": courant}),
        *_month_routes("budget_period", "/analytics/budget-period"),
        ("budget_period_default", "/analytics/budget-period", {}),
        ("audit", "/analytics/audit", {}),
        ("actions", "/analytics/actions", {}),
        *_month_routes("tags", "/analytics/tags"),
        ("tags_range", "/analytics/tags", {"start_date": "2026-01-01T00:00:00", "end_date": "2026-06-15T00:00:00"}),
        *_month_routes("expenses_by_category", "/analytics/expenses-by-category"),
        *_month_routes("expenses_by_category_courant", "/analytics/expenses-by-category", {"account_id": courant}),
        *_month_routes("top_merchants", "/analytics/top-merchants", {"limit": 10}),
        *_month_routes("top_merchants_courant", "/analytics/top-merchants", {"account_id": courant}),
        ("account_flow_summary", "/analytics/account-flow-summary", {"account_id": courant}),
        ("account_flow_summary_range", "/analytics/account-flow-summary",
         {"account_id": courant, "start_date": "2026-01-01T00:00:00", "end_date": "2026-05-31T23:59:59"}),
        ("kpi_history", "/analytics/kpi-history", {"months_count": 12}),
        ("kpi_history_courant", "/analytics/kpi-history", {"months_count": 12, "account_id": courant}),
        ("timeseries_2026", "/analytics/timeseries", {"year": 2026}),
        ("timeseries_2025", "/analytics/timeseries", {"year": 2025}),
        ("timeseries_2026_courant", "/analytics/timeseries", {"year": 2026, "account_id": courant}),
        *_month_routes("calendar", "/analytics/calendar"),
        *_month_routes("calendar_courant", "/analytics/calendar", {"account_id": courant}),
        ("cashflow_30", "/analytics/cashflow-projection", {"days": 30}),
        ("cashflow_90", "/analytics/cashflow-projection", {"days": 90}),
        ("cashflow_90_courant", "/analytics/cashflow-projection", {"days": 90, "account_id": courant}),
        *_month_routes("monthly_report", "/analytics/monthly-report"),
        *_month_routes("monthly_report_courant", "/analytics/monthly-report", {"account_id": courant}),
        *_month_routes("money_flow", "/analytics/money-flow"),
        *_month_routes("money_flow_courant", "/analytics/money-flow", {"account_id": courant}),
        *_month_routes("sankey", "/analytics/sankey"),
        *_month_routes("sankey_courant", "/analytics/sankey", {"account_id": courant}),
        *_month_routes("insights", "/analytics/insights"),
        *_month_routes("insights_courant", "/analytics/insights", {"account_id": courant}),
        ("subscriptions", "/analytics/subscriptions", {}),
        ("subscriptions_other", "/analytics/subscriptions", {"include_other": True}),
        ("subscriptions_courant", "/analytics/subscriptions", {"account_id": courant}),
        ("wrapped_2025", "/analytics/wrapped", {"year": 2025}),
        ("wrapped_2026", "/analytics/wrapped", {"year": 2026}),
        ("investments", "/analytics/investments", {}),
        *_month_routes("investments", "/analytics/investments"),
        ("investments_pea", "/analytics/investments", {"account_id": accounts["investissement"]}),
        ("investments_allocation", "/analytics/investments-allocation", {}),
        ("investments_allocation_pea", "/analytics/investments-allocation", {"account_id": accounts["investissement"]}),
        ("investments_allocation_advanced", "/analytics/investments-allocation-advanced", {}),
        ("patrimoine_allocation", "/analytics/patrimoine-allocation", {}),
        ("wealth_forecast", "/analytics/wealth-forecast", {}),
        ("wealth_forecast_params", "/analytics/wealth-forecast",
         {"years": 20, "extra_monthly": 200, "monthly_savings": 900, "investment_return_pct": 5, "savings_return_pct": 2}),
        ("fire", "/analytics/fire", {}),
        ("fire_params", "/analytics/fire",
         {"withdrawal_rate_pct": 3.5, "inflation_pct": 2.5, "return_pct": 6, "monthly_savings": 1200, "annual_expenses": 30000}),
        ("allocation_suggestions", "/analytics/asset-allocation/suggestions", {}),
        ("wealth_simulation", "/analytics/wealth-simulation", SIM),
        ("wealth_simulation_volatility", "/analytics/wealth-simulation", {**SIM, "volatility_pct": 15}),
        ("wealth_simulation_full", "/analytics/wealth-simulation",
         {**SIM, "inflation_rate_pct": 2, "contribution_indexation_pct": 1, "tax_rate_pct": 30,
          "tax_deferred": False, "events": EVENTS}),
        ("tax_overview", "/tax/overview", {}),
        ("tax_annual_report_2025", "/tax/annual-report", {"year": 2025}),
        ("month_review_2026_05", "/month-review", {"year": 2026, "month": 5}),
    ]
    for kind in ("investissement", "assurance_vie"):
        account_id = accounts[kind]
        routes.append((f"investment_{kind}", f"/analytics/investments/{account_id}", {}))
        routes.append((f"investment_{kind}_history", f"/analytics/investments/{account_id}/performance-history", {}))
    return routes


def _tx(db, account: Account, day: date, merchant: str, amount: float, type_: str = "Sortie", category_id=None) -> Transaction:
    tx = Transaction(
        account_id=account.id, date=datetime(day.year, day.month, day.day), month_label=f"{day.year}-{day.month:02d}",
        type=type_, merchant=merchant, category_id=category_id, amount=amount, currency=account.currency,
        original_amount=amount, running_balance=0.0,
    )
    db.add(tx)
    return tx


def _add_action_center_cases(db) -> None:
    """Compléments au jeu de démo pour que chaque règle du Centre d'Actions produise une action."""
    accounts = {a.type: a for a in db.query(Account).order_by(Account.id).all()}
    courant, epargne, pea = accounts["courant"], accounts["epargne"], accounts["investissement"]
    # Budget dépassé (catégorie aussi des lignes suivantes : une hausse « non catégorisé » ×2 fait
    # planter /insights, bogue existant hors périmètre de la migration)
    loisirs = Category(name="Instantané loisirs", type="depense", monthly_limit=20.0)
    db.add(loisirs)
    db.flush()
    _tx(db, courant, date(2026, 6, 4), "CINEMA", 45.0, category_id=loisirs.id)
    # Virement non rapproché
    _tx(db, courant, date(2026, 6, 1), "VIR SANS LIEN", 777.0, category_id=loisirs.id)
    _tx(db, epargne, date(2026, 6, 2), "VIR RECU SANS LIEN", 777.0, "Entree")
    # Sans catégorie, règle suggérée, doublon et variantes d'un même marchand
    for day in (date(2026, 2, 7), date(2026, 3, 7), date(2026, 4, 7), date(2026, 5, 7), date(2026, 6, 6), date(2026, 6, 6)):
        _tx(db, courant, day, "BOULANGERIE DUPONT", 12.4)
    _tx(db, courant, date(2026, 6, 9), "Boulangerie Dupont 75", 8.1)
    # Remboursement reçu non affecté, avec une créance ouverte
    remb_cat = db.query(Category).filter(Category.name == "Remboursement (recu)").one()
    avance = _tx(db, courant, date(2026, 5, 20), "RESTAURANT AVANCE", 90.0)
    _tx(db, courant, date(2026, 6, 3), "VIR AMI REMBOURSEMENT", 30.0, "Entree", remb_cat.id)
    db.flush()
    db.add(ReimbursementClaim(transaction_id=avance.id, debtor="Ami", expected_amount=60.0))
    # Hausse de prix d'abonnement
    for month in (1, 2, 3, 4):
        _tx(db, courant, date(2026, month, 10), "STREAMFLIX", 13.49, category_id=loisirs.id)
    for month in (5, 6):
        _tx(db, courant, date(2026, month, 10), "STREAMFLIX", 15.99, category_id=loisirs.id)
    # Salaire configuré sans mois renseigné (sur l'épargne : aucune entrée « salaire » n'y figure)
    db.add(SalaryConfig(salary_account_id=epargne.id, net_salary=2500.0, ticket_value=9.0, ticket_employee_share=4.5,
                        is_active=True, created_at=datetime(2026, 1, 1)))
    # Dividende sans titre, titre distribuant sans dividende depuis 13 mois
    db.add(InvestmentTransaction(account_id=pea.id, date=datetime(2026, 3, 2), type="dividende", amount=4.2,
                                 currency="EUR", original_amount=4.2))
    holding = db.query(PortfolioHolding).filter(PortfolioHolding.account_id == pea.id).order_by(PortfolioHolding.ticker).first()
    holding.pays_dividends = True
    holding.created_at = datetime(2024, 1, 1)
    # « reconciliation-gap » exige un Point Zéro, absent de la démo : couvert par tests/test_portfolio.py
    db.flush()
    for account in (courant, epargne):
        recalculate_running_balances(db, account.id)
    db.commit()


@pytest.fixture()
def snapshot_client(client, db_session, monkeypatch, tmp_path):
    async def no_chart(http_client, sym, params):
        return None

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "status.json").write_text(json.dumps({"last_error": "disque plein", "last_error_at": "2026-06-14T03:00:00+00:00"}))
    monkeypatch.setenv("BACKUP_DIR", str(backup_dir))
    monkeypatch.setattr(yahoo_finance, "fetch_chart", no_chart)
    market_quotes._QUOTES_CACHE.clear()
    currency_mod._rates_cache.clear()
    currency_mod._cache_expiry.clear()
    with freeze_time(FROZEN_NOW, tick=False, real_asyncio=True):
        asyncio.run(generate_demo_data(db_session, today=TODAY))
        _add_action_center_cases(db_session)
        yield client
    market_quotes._QUOTES_CACHE.clear()
    currency_mod._rates_cache.clear()
    currency_mod._cache_expiry.clear()


def _fetch(client, path: str, params: dict):
    random.seed(1234)  # simulation avec volatilité : tirages reproductibles
    response = client.get(path, params=params)
    assert response.status_code == 200, f"{path} {params} → {response.status_code} {response.text[:300]}"
    return _normalize(response.json())


def test_analytics_snapshots(snapshot_client, db_session):
    client = snapshot_client
    accounts = {a.type: a.id for a in db_session.query(Account).order_by(Account.id).all()}
    results = {name: _fetch(client, path, params) for name, path, params in _routes(accounts)}
    for issue in results["audit"].get("issues", []):
        issue_id = issue["id"]
        response = client.get(f"/analytics/audit/{issue_id}")
        if response.status_code == 200:
            results[f"audit_issue_{issue_id}"] = _normalize(response.json())

    update = os.environ.get("UPDATE_SNAPSHOTS") == "1"
    if update:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        for old in SNAPSHOT_DIR.glob("*.json"):
            old.unlink()
    failures = []
    for name, actual in results.items():
        file = SNAPSHOT_DIR / f"{name}.json"
        if update:
            file.write_text(json.dumps(actual, ensure_ascii=False, indent=1) + "\n")
            continue
        if not file.exists():
            failures.append(f"{name}: instantané absent")
            continue
        diff = _first_diff(json.loads(file.read_text()), actual)
        if diff:
            failures.append(f"{name}: {diff}")
    if not update:
        stored = {p.stem for p in SNAPSHOT_DIR.glob("*.json")}
        failures += [f"{name}: instantané orphelin" for name in sorted(stored - set(results))]
    assert not failures, "\n".join(failures)
