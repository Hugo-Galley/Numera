"""Versements automatiques à relier à un titre : ceux qu'une récurrence a créés sans titre."""
from datetime import datetime

import pytest
from freezegun import freeze_time

from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.recurring_transaction import RecurringTransaction


@pytest.fixture()
def cto(db_session) -> Account:
    account = Account(name="CTO", type="investissement", currency="EUR")
    db_session.add(account)
    db_session.commit()
    return account


@pytest.fixture()
def rule(db_session, cto) -> RecurringTransaction:
    courant = Account(name="Courant", type="courant", currency="EUR")
    db_session.add(courant)
    db_session.flush()
    rd = RecurringTransaction(
        account_id=courant.id, name="Alimentation CTO", type="Sortie", amount=50.0, currency="EUR",
        frequency="monthly", day_of_month=29, start_date=datetime(2026, 1, 1), transfer_to_account_id=cto.id,
    )
    db_session.add(rd)
    db_session.commit()
    return rd


def _deposit(db, account_id: int, day: datetime, **fields) -> InvestmentTransaction:
    tx = InvestmentTransaction(account_id=account_id, date=day, type="versement", amount=50.0, original_amount=50.0,
                               currency="EUR", **fields)
    db.add(tx)
    db.commit()
    return tx


def _unassigned_ids(client, account_id: int) -> list[int]:
    resp = client.get(f"/investment-transactions?account_id={account_id}&unassigned=true")
    assert resp.status_code == 200
    return [row["id"] for row in resp.json()]


@freeze_time("2026-11-15 12:00")
def test_only_untitled_deposits_from_a_recurring_rule_are_to_assign(client, db_session, cto, rule):
    auto = _deposit(db_session, cto.id, datetime(2026, 10, 29), recurring_transaction_id=rule.id)
    _deposit(db_session, cto.id, datetime(2026, 10, 1), note="Achat Apple")  # saisie manuelle : pas concernée
    _deposit(db_session, cto.id, datetime(2026, 9, 29), recurring_transaction_id=rule.id, ticker="AAPL", quantity=0.2)
    _deposit(db_session, cto.id, datetime(2026, 11, 29), recurring_transaction_id=rule.id)  # à venir
    other = Account(name="PEA", type="investissement", currency="EUR")
    db_session.add(other)
    db_session.commit()
    _deposit(db_session, other.id, datetime(2026, 10, 29), recurring_transaction_id=rule.id)

    assert _unassigned_ids(client, cto.id) == [auto.id]


@freeze_time("2026-11-15 12:00")
def test_deposit_kept_as_cash_is_no_longer_proposed(client, db_session, cto, rule):
    auto = _deposit(db_session, cto.id, datetime(2026, 10, 29), recurring_transaction_id=rule.id)

    resp = client.patch(f"/investment-transactions/{auto.id}", json={"kept_as_cash": True})

    assert resp.status_code == 200
    assert resp.json()["kept_as_cash"] is True
    db_session.expire_all()
    assert db_session.get(InvestmentTransaction, auto.id).kept_as_cash is True
    assert _unassigned_ids(client, cto.id) == []


@freeze_time("2026-11-15 12:00")
def test_assigning_a_security_updates_the_position_and_clears_the_prompt(client, db_session, cto, rule):
    auto = _deposit(db_session, cto.id, datetime(2026, 10, 29), recurring_transaction_id=rule.id)

    resp = client.patch(f"/investment-transactions/{auto.id}", json={"ticker": "aapl", "quantity": 0.25, "unit_price": 200.0})

    assert resp.status_code == 200
    db_session.expire_all()
    holding = db_session.query(PortfolioHolding).filter_by(account_id=cto.id, ticker="AAPL").one()
    assert holding.quantity == pytest.approx(0.25)
    assert _unassigned_ids(client, cto.id) == []


def test_read_exposes_the_recurring_rule_of_a_deposit(client, db_session, cto, rule):
    auto = _deposit(db_session, cto.id, datetime(2026, 10, 29), recurring_transaction_id=rule.id)

    rows = client.get(f"/investment-transactions?account_id={cto.id}").json()

    assert rows[0]["id"] == auto.id
    assert rows[0]["recurring_transaction_id"] == rule.id
    assert rows[0]["kept_as_cash"] is False


def _price_on(price: float, currency: str):
    async def fake(db, ticker, day, max_gap_days=7):
        return {"price": price, "currency": currency, "date": day.isoformat()}
    return fake


def test_security_proposal_sizes_the_deposit_at_the_close_of_its_day(client, db_session, cto, rule, monkeypatch):
    from app.services.investissement import investment_transactions as service
    auto = _deposit(db_session, cto.id, datetime(2026, 10, 29), recurring_transaction_id=rule.id)
    monkeypatch.setattr(service.market_quotes, "get_price_on", _price_on(200.0, "EUR"))

    resp = client.get(f"/investment-transactions/{auto.id}/security-proposal?ticker=aapl")

    assert resp.status_code == 200
    assert resp.json() == {"ticker": "AAPL", "quantity": 0.25, "unit_price": 200.0, "price_currency": "EUR",
                           "price_date": "2026-10-29"}


def test_security_proposal_without_a_known_price_leaves_the_size_empty(client, db_session, cto, rule, monkeypatch):
    from app.services.investissement import investment_transactions as service

    async def no_price(db, ticker, day, max_gap_days=7):
        return None

    auto = _deposit(db_session, cto.id, datetime(2026, 10, 29), recurring_transaction_id=rule.id)
    monkeypatch.setattr(service.market_quotes, "get_price_on", no_price)

    resp = client.get(f"/investment-transactions/{auto.id}/security-proposal?ticker=AAPL")

    assert resp.json() == {"ticker": "AAPL", "quantity": None, "unit_price": None, "price_currency": None, "price_date": None}


def test_security_proposal_of_an_unknown_deposit_is_not_found(client):
    assert client.get("/investment-transactions/999/security-proposal?ticker=AAPL").status_code == 404
