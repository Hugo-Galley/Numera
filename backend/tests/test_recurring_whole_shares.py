"""Achats programmés en parts entières (PEA) : quantité arrondie à l'entier, montant = parts × cours."""
import asyncio
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.recurring import generate_recurring_transactions
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from tests.test_recurring_deferred_credit import deferred_rule
from tests.test_recurring_transfers import accounts, fake_market, recurring


def test_whole_shares_transfer_credits_only_the_cost_of_the_shares(db_session: Session, monkeypatch):
    fake_market(monkeypatch)  # cours historique = 100 + jour du mois (116 le 16)
    main, pea = accounts(db_session, dest_type="investissement")
    deferred_rule(db_session, main, pea, ticker="CW8.PA", whole_shares=True)

    asyncio.run(generate_recurring_transactions(db_session))

    versements = db_session.query(InvestmentTransaction).filter_by(account_id=pea.id, type="versement").all()
    assert len(versements) >= 2
    for v in versements:
        assert v.quantity == 3.0 and v.unit_price == 116.0  # 400 / 116 = 3,45 -> 3 parts
        assert v.amount == v.original_amount == 348.0  # coût réel des parts, pas les 400 € prévus
        sortie = db_session.get(Transaction, v.linked_transaction_id)
        assert sortie.amount == 400.0  # le virement bancaire reste de 400 €, le reliquat reste chez le courtier
        assert sortie.linked_investment_transaction_id == v.id and v.link_origin == "recurring"

    holding = db_session.query(PortfolioHolding).filter_by(account_id=pea.id, ticker="CW8.PA").one()
    assert holding.quantity == 3.0 * len(versements)
    assert holding.buy_price_avg == 116.0

    before = db_session.query(InvestmentTransaction).count()
    asyncio.run(generate_recurring_transactions(db_session))
    assert db_session.query(InvestmentTransaction).count() == before  # idempotent


def test_fractional_behaviour_is_unchanged_without_the_option(db_session: Session, monkeypatch):
    fake_market(monkeypatch)
    main, pea = accounts(db_session, dest_type="investissement")
    deferred_rule(db_session, main, pea, ticker="CW8.PA")

    asyncio.run(generate_recurring_transactions(db_session))

    for v in db_session.query(InvestmentTransaction).filter_by(account_id=pea.id, type="versement").all():
        assert v.amount == 400.0
        assert abs(v.quantity - 400.0 / 116.0) < 1e-5


def test_whole_shares_keeps_fractional_when_amount_is_below_one_share(db_session: Session, monkeypatch):
    fake_market(monkeypatch)
    main, pea = accounts(db_session, dest_type="investissement")
    rd = deferred_rule(db_session, main, pea, ticker="CW8.PA", whole_shares=True)
    rd.amount = 50.0  # moins que le prix d'une part (116 €) : pas d'achat nul
    db_session.commit()

    asyncio.run(generate_recurring_transactions(db_session))

    versements = db_session.query(InvestmentTransaction).filter_by(account_id=pea.id, type="versement").all()
    assert versements
    for v in versements:
        assert v.amount == 50.0 and 0 < v.quantity < 1


def test_whole_shares_on_the_investment_account_itself(db_session: Session, monkeypatch):
    fake_market(monkeypatch)
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(pea)
    db_session.commit()
    past = datetime.now() - timedelta(days=45)
    rd = RecurringTransaction(
        account_id=pea.id, name="Plan PEA", type="versement", amount=400.0, currency="EUR", frequency="monthly",
        day_of_month=16, start_date=past, is_active=True, auto_generate=True, ticker="CW8.PA", whole_shares=True,
    )
    db_session.add(rd)
    db_session.commit()

    asyncio.run(generate_recurring_transactions(db_session))

    txs = db_session.query(InvestmentTransaction).filter_by(recurring_transaction_id=rd.id).all()
    assert txs
    for t in txs:
        assert t.quantity == 3.0 and t.unit_price == 116.0
        assert t.amount == t.original_amount == 348.0


def test_whole_shares_flag_roundtrip_through_the_api(client: TestClient, db_session: Session):
    main, pea = accounts(db_session, dest_type="investissement")
    base = {
        "account_id": main.id, "name": "Alimentation PEA", "type": "Sortie", "amount": 400.0, "currency": "EUR",
        "frequency": "monthly", "day_of_month": 1, "start_date": "2026-01-01T00:00:00",
        "transfer_to_account_id": pea.id, "ticker": "CW8.PA",
    }
    created = client.post("/recurring-transactions/", json=base)
    assert created.status_code == 200, created.text
    assert created.json()["whole_shares"] is False  # défaut

    rid = created.json()["id"]
    updated = client.patch(f"/recurring-transactions/{rid}", json={"whole_shares": True})
    assert updated.status_code == 200, updated.text
    db_session.expire_all()
    assert db_session.get(RecurringTransaction, rid).whole_shares is True
    assert client.get("/recurring-transactions/").json()[0]["whole_shares"] is True
