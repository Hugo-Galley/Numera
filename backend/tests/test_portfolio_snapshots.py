"""Instantanés des routes du portefeuille (positions, valorisation, dividendes, diversification), à date figée.

Complète `test_analytics_snapshots.py` (mêmes données de démo, même fixture) avec un compte titres doté d'un
Point Zéro, seul cas où la courbe, le TWR et le rapprochement courtier sont calculés. Ne jamais régénérer
pour faire passer le test : un écart est un bug. Régénération volontaire :
`UPDATE_SNAPSHOTS=1 PYTHONPATH=. python3.11 -m pytest tests/test_portfolio_snapshots.py`.
"""
import asyncio
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

import app.integrations.currency as currency_mod
import app.integrations.yahoo_finance as yahoo_finance
from app.models.account import Account
from app.services.investissement.holdings.rebuild import rebuild_holdings
from app.models.balance_snapshot import BalanceSnapshot
from app.models.holding_baseline_item import HoldingBaselineItem
from app.models.investment_transaction import InvestmentTransaction
from app.models.security_price import SecurityPrice
from test_analytics_snapshots import _first_diff, _normalize, snapshot_client  # noqa: F401 (fixture)

SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "portfolio"
BASELINE = datetime(2025, 6, 2, 10, 0)
PRICE_START, PRICE_END = date(2025, 5, 1), date(2026, 6, 15)


def _usd_rate(day: date) -> float:
    """Taux EUR→USD déterministe, variable d'un mois à l'autre (effet de change non nul)."""
    return round(1.05 + (day.month % 4) * 0.02, 4)


def _store_prices(db) -> None:
    span = (PRICE_END - PRICE_START).days
    day = PRICE_START
    while day <= PRICE_END:
        progress = (day - PRICE_START).days / span
        db.add(SecurityPrice(ticker="ESE.PA", date=day, close=round(400 + 80 * progress, 2), currency="EUR", source="yahoo"))
        db.add(SecurityPrice(ticker="AAPL", date=day, close=round(150 + 40 * progress, 2), currency="USD", source="yahoo"))
        day += timedelta(days=7)
    db.add(SecurityPrice(ticker="ESE.PA", date=PRICE_END, close=481.0, currency="EUR", source="yahoo"))
    db.add(SecurityPrice(ticker="AAPL", date=PRICE_END, close=191.0, currency="USD", source="yahoo"))


def _operation(account_id: int, day: str, tx_type: str, amount: float, currency: str = "EUR", **extra) -> InvestmentTransaction:
    """Opération telle que l'API l'enregistrerait (montant converti dans la devise du compte, ici l'EUR)."""
    when = datetime.fromisoformat(day)
    converted = amount if currency == "EUR" else round(amount / _usd_rate(when.date()), 2)
    return InvestmentTransaction(account_id=account_id, date=when, type=tx_type, amount=converted, currency=currency,
                                 original_amount=amount, **extra)


def _add_portfolio_cases(db) -> dict[str, int]:
    """Compte titres avec Point Zéro, achats, vente, frais, dividende avec retenue et relevés du courtier.

    Insertion directe en base : sous `freezegun`, Pydantic ne sait pas valider un corps de requête daté.
    """
    cto = Account(name="CTO Instantané", type="investissement", currency="EUR", institution="Courtier Instantané",
                  valuation_mode="positions", opened_at=datetime(2025, 1, 1), holdings_baseline_date=BASELINE)
    db.add(cto)
    _store_prices(db)
    db.flush()
    db.add(BalanceSnapshot(account_id=cto.id, date=BASELINE, current_value=5000.0, note="Point zéro", is_zero_point=True))
    for day, value in ((datetime(2025, 9, 1, 10), 6200.0), (datetime(2026, 1, 5, 10), 6500.0), (datetime(2026, 5, 4, 10), 7200.0)):
        db.add(BalanceSnapshot(account_id=cto.id, date=day, current_value=value, note="Relevé courtier"))
    for ticker, name, quantity, pru, currency in (("ESE.PA", "BNP Paribas Easy S&P 500", 10, 400.0, "EUR"),
                                                  ("AAPL", "Apple Inc", 5, 150.0, "USD")):
        db.add(HoldingBaselineItem(account_id=cto.id, baseline_date=BASELINE, ticker=ticker, asset_name=name,
                                   quantity=quantity, buy_price_avg=pru, currency=currency))
    db.add_all([
        # Antérieures au Point Zéro : ignorées par le rejeu, utilisées par l'estimation du PRU
        _operation(cto.id, "2025-03-10T09:00:00", "achat", 1520.0, ticker="ESE.PA", quantity=4, unit_price=380.0,
                   price_currency="EUR", note="Achat ESE"),
        _operation(cto.id, "2025-04-14T09:00:00", "versement", 700.0, note="Achat Apple"),
        _operation(cto.id, "2025-07-01T09:00:00", "versement", 2000.0),
        _operation(cto.id, "2025-07-03T09:00:00", "achat", 1262.0, ticker="ESE.PA", quantity=3, unit_price=420.0,
                   price_currency="EUR", fees=2.0, note="Achat ESE"),
        _operation(cto.id, "2025-11-10T15:00:00", "vente", 339.0, "USD", ticker="AAPL", quantity=2, unit_price=170.0,
                   price_currency="USD", fees=1.0, note="Vente Apple"),
        _operation(cto.id, "2025-12-31T12:00:00", "frais", 5.0, note="Droits de garde"),
        _operation(cto.id, "2026-02-16T12:00:00", "dividende", 12.0, ticker="ESE.PA", withholding_tax=3.0,
                   note="Dividende ESE"),
    ])
    db.flush()
    asyncio.run(rebuild_holdings(db, cto.id))
    db.commit()
    return {"cto": cto.id}


def _routes(accounts: dict[str, int]) -> list[tuple[str, str, dict]]:
    pea, av, cto = accounts["investissement"], accounts["assurance_vie"], accounts["cto"]
    return [
        ("portfolio", "/analytics/portfolio", {}),
        ("portfolio_pea", f"/analytics/portfolio/{pea}", {}),
        ("portfolio_av", f"/analytics/portfolio/{av}", {}),
        ("portfolio_cto", f"/analytics/portfolio/{cto}", {}),
        ("dividends", "/analytics/dividends", {}),
        ("dividends_12", "/analytics/dividends", {"months": 12}),
        ("dividends_pea", "/analytics/dividends", {"account_id": pea}),
        ("dividends_cto", "/analytics/dividends", {"account_id": cto}),
        ("holdings", "/holdings", {}),
        ("holdings_pea", "/holdings", {"account_id": pea}),
        ("holdings_cto", "/holdings", {"account_id": cto}),
        ("estimate_costs_cto", "/holdings/estimate-costs", {"account_id": cto}),
        ("investment_transactions_cto", "/investment-transactions", {"account_id": cto}),
        ("diversity", "/analytics/diversity-scanner", {}),
        ("diversity_pea", "/analytics/diversity-scanner", {"account_id": pea}),
        ("etf_profiles", "/etf-profiles", {}),
        ("investment_cto", f"/analytics/investments/{cto}", {}),
        ("investment_cto_history", f"/analytics/investments/{cto}/performance-history", {}),
        ("actions", "/analytics/actions", {}),
    ]


@pytest.fixture()
def portfolio_client(snapshot_client, db_session, monkeypatch):
    async def no_composition(symbol):
        return None

    async def historical_rate(db, day, currency, base="EUR"):
        return 1.0 if currency == "EUR" else _usd_rate(day)

    monkeypatch.setattr(yahoo_finance, "fetch_composition", no_composition)
    monkeypatch.setattr(currency_mod, "get_historical_rate", historical_rate)
    accounts = {a.type: a.id for a in db_session.query(Account).order_by(Account.id).all()}
    accounts.update(_add_portfolio_cases(db_session))
    yield snapshot_client, accounts


def test_portfolio_snapshots(portfolio_client):
    client, accounts = portfolio_client
    results = {}
    for name, path, params in _routes(accounts):
        response = client.get(path, params=params)
        assert response.status_code == 200, f"{path} {params} → {response.status_code} {response.text[:300]}"
        results[name] = _normalize(response.json())

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
