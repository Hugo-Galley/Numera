"""Valeur d'un compte : la page Comptes, le scanner de diversité et la projection de trésorerie suivent `account_values`."""
from datetime import datetime, timedelta

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.transaction import Transaction

NOW = datetime.now()


def _tx(account_id, when, balance):
    return Transaction(
        account_id=account_id, date=when, month_label=when.strftime("%Y-%m"), type="Entree", merchant="M",
        amount=10.0, original_amount=10.0, currency="EUR", running_balance=balance,
    )


def _livret_with_stale_snapshot(db):
    livret = Account(name="Livret", type="epargne", currency="EUR", active=True)
    db.add(livret)
    db.flush()
    db.add(BalanceSnapshot(account_id=livret.id, date=NOW - timedelta(days=365), current_value=100.0))
    db.add(_tx(livret.id, NOW - timedelta(days=2), 500.0))
    db.commit()
    return livret


def test_diversity_wealth_view_uses_most_recent_source(client, db_session):
    """Un relevé de livret vieux d'un an ne masque pas les mouvements postérieurs."""
    _livret_with_stale_snapshot(db_session)

    totals = client.get("/analytics/diversity-scanner").json()["totals"]

    assert totals["epargne_eur"] == 500.0


def test_diversity_wealth_view_keeps_negative_balances(client, db_session):
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(courant)
    db_session.flush()
    db_session.add(_tx(courant.id, NOW - timedelta(days=1), -50.0))
    db_session.commit()

    totals = client.get("/analytics/diversity-scanner").json()["totals"]

    assert totals["courant_eur"] == -50.0  # comme patrimoine-allocation (account_values)


def test_cashflow_current_balance_uses_most_recent_source(client, db_session):
    livret = _livret_with_stale_snapshot(db_session)
    db_session.add(BalanceSnapshot(account_id=livret.id, date=NOW - timedelta(hours=1), current_value=900.0))
    db_session.commit()

    body = client.get(f"/analytics/cashflow-projection?days=30&account_id={livret.id}").json()

    assert body["current_balance"] == 900.0


def test_accounts_page_balance_matches_wealth_value_for_investment_account(client, db_session):
    """Un compte d'investissement garde son dernier relevé, même si une opération est plus récente (comme le patrimoine)."""
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(pea)
    db_session.flush()
    db_session.add(BalanceSnapshot(account_id=pea.id, date=NOW - timedelta(days=30), current_value=1000.0))
    db_session.add(_tx(pea.id, NOW - timedelta(days=2), 300.0))
    db_session.commit()

    [account] = client.get("/accounts").json()
    allocation = client.get("/analytics/patrimoine-allocation").json()

    assert account["balance"] == 1000.0
    assert "1000" in str(allocation)


def test_accounts_page_and_cashflow_use_positions_value(client, db_session, monkeypatch):
    """Un compte titres valorisé par ses positions affiche cette valeur partout (avant : 0, ses seules opérations)."""
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(pea)
    db_session.commit()
    pea_id = pea.id

    async def fake_positions(db, accounts):
        return {a.id: 5000.0 for a in accounts if a.type == "investissement"}

    monkeypatch.setattr("app.services.comptes.wealth.positions_values_eur", fake_positions)

    [account] = client.get("/accounts").json()
    cashflow = client.get("/analytics/cashflow-projection?days=30").json()

    assert account["balance"] == 5000.0
    assert cashflow["current_balance"] == 5000.0
    assert pea_id == account["id"]


def test_investments_overview_counts_snapshot_dated_later_today(client, db_session):
    """Même borne exclusive (fin de journée) que le patrimoine : un relevé daté d'aujourd'hui compte (règle 12)."""
    av = Account(name="AV", type="assurance_vie", currency="EUR", active=True, valuation_mode="snapshot")
    db_session.add(av)
    db_session.flush()
    later_today = datetime.now().replace(hour=23, minute=59, second=0, microsecond=0)
    db_session.add(BalanceSnapshot(account_id=av.id, date=later_today, current_value=777.0))
    db_session.commit()

    overview = client.get("/analytics/investments").json()

    [item] = [i for i in overview["items"] if i["account_id"] == av.id]
    assert item["current_value"] == 777.0
