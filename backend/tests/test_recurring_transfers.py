import asyncio
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.recurring import generate_recurring_transactions
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction


def accounts(db: Session, dest_type="epargne", dest_currency="EUR"):
    a = Account(name="Principal", type="courant", currency="EUR", active=True)
    b = Account(name="Destination", type=dest_type, currency=dest_currency, active=True)
    db.add_all([a, b])
    db.commit()
    return a, b


def recurring(db, src, dest_id, **kw):
    r = RecurringTransaction(
        account_id=src.id, name="Épargne mensuelle", type="Sortie", amount=500.0, currency="EUR",
        frequency="monthly", day_of_month=5, start_date=datetime.now() - timedelta(days=75),
        is_active=True, auto_generate=True, transfer_to_account_id=dest_id, **kw,
    )
    db.add(r)
    db.commit()
    return r


def test_transfer_recurrence_creates_both_legs_linked(db_session: Session):
    main, livret = accounts(db_session)
    rd = recurring(db_session, main, livret.id)

    assert asyncio.run(generate_recurring_transactions(db_session)) >= 2

    sorties = db_session.query(Transaction).filter_by(account_id=main.id, type="Sortie").all()
    entrees = db_session.query(Transaction).filter_by(account_id=livret.id, type="Entree").all()
    assert len(sorties) == len(entrees) >= 2
    for s in sorties:
        e = db_session.get(Transaction, s.linked_transaction_id)
        assert e.account_id == livret.id and e.linked_transaction_id == s.id
        assert s.is_transfer and e.is_transfer
        assert s.link_origin == e.link_origin == "recurring"
        assert e.amount == 500.0 and e.recurring_transaction_id == rd.id
    # soldes recalculés des deux côtés
    assert max(e.running_balance for e in entrees) == 500.0 * len(entrees)

    before = db_session.query(Transaction).count()
    asyncio.run(generate_recurring_transactions(db_session))
    assert db_session.query(Transaction).count() == before  # idempotent


def test_transfer_recurrence_to_investment_account_creates_versement(db_session: Session):
    main, broker = accounts(db_session, dest_type="investissement")
    recurring(db_session, main, broker.id)
    asyncio.run(generate_recurring_transactions(db_session))

    versements = db_session.query(InvestmentTransaction).filter_by(account_id=broker.id, type="versement").all()
    assert versements
    for v in versements:
        s = db_session.get(Transaction, v.linked_transaction_id)
        assert s.linked_investment_transaction_id == v.id and v.link_origin == "recurring"


def test_transfer_recurrence_validation(client, db_session: Session):
    main, livret = accounts(db_session)
    base = {"account_id": main.id, "name": "x", "type": "Sortie", "amount": 10, "frequency": "monthly",
            "day_of_month": 1, "start_date": "2026-01-01T00:00:00"}
    assert client.post("/recurring-transactions/", json={**base, "transfer_to_account_id": livret.id}).status_code == 200
    assert client.post("/recurring-transactions/", json={**base, "transfer_to_account_id": main.id}).status_code == 422
    assert client.post("/recurring-transactions/", json={**base, "type": "Entree", "transfer_to_account_id": livret.id}).status_code == 422
    assert client.post("/recurring-transactions/", json={**base, "transfer_to_account_id": 999}).status_code == 404


# ─── DCA : virement + achat de parts en un seul mouvement ─────────────────────

from datetime import date as date_type

from app.core import market_data
from app.models.portfolio_holding import PortfolioHolding


def fake_market(monkeypatch):
    """Cours historique = 100 + jour du mois ; cotation en direct = 999 (ne doit pas servir aux échéances passées)."""
    async def fake_price_on(db, ticker, day, max_gap_days=7):
        return {"price": 100.0 + day.day, "currency": "EUR", "date": day.isoformat()}

    async def fake_quotes(symbols, db=None):
        return {s: {"price": 999.0, "currency": "EUR"} for s in symbols}

    monkeypatch.setattr(market_data, "get_price_on", fake_price_on)
    monkeypatch.setattr(market_data, "get_market_quotes", fake_quotes)


def test_dca_transfer_buys_shares_at_historical_price(db_session: Session, monkeypatch):
    fake_market(monkeypatch)
    main, pea = accounts(db_session, dest_type="investissement")
    rd = recurring(db_session, main, pea.id, ticker="CW8.PA")

    asyncio.run(generate_recurring_transactions(db_session))

    versements = db_session.query(InvestmentTransaction).filter_by(account_id=pea.id, type="versement").all()
    past = [v for v in versements if v.date.date() < date_type.today()]
    assert len(past) >= 2
    for v in past:
        price = 100.0 + v.date.day
        assert v.ticker == "CW8.PA"
        assert v.unit_price == price
        assert abs(v.quantity - 500.0 / price) < 1e-5
        s = db_session.get(Transaction, v.linked_transaction_id)
        assert s.account_id == main.id and s.type == "Sortie" and s.linked_investment_transaction_id == v.id
        assert v.link_origin == s.link_origin == "recurring"

    holding = db_session.query(PortfolioHolding).filter_by(account_id=pea.id, ticker="CW8.PA").one()
    assert abs(holding.quantity - sum(v.quantity for v in versements)) < 1e-5
    # un seul dépôt par échéance : le montant investi n'est pas doublé
    assert sum(v.amount for v in versements) == 500.0 * len(versements)
    # la sortie du compte source n'a ni titre ni quantité
    assert db_session.query(InvestmentTransaction).filter_by(account_id=main.id).count() == 0


def test_dca_on_investment_account_uses_historical_price_when_backfilled(db_session: Session, monkeypatch):
    fake_market(monkeypatch)
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(pea)
    db_session.commit()
    start = datetime.now() - timedelta(days=80)
    rd = RecurringTransaction(
        account_id=pea.id, name="DCA", type="versement", amount=300.0, currency="EUR", frequency="monthly",
        day_of_month=start.day, start_date=start, is_active=True, auto_generate=True, ticker="CW8.PA",
    )
    db_session.add(rd)
    db_session.commit()

    asyncio.run(generate_recurring_transactions(db_session))

    txs = db_session.query(InvestmentTransaction).filter_by(recurring_transaction_id=rd.id).all()
    past = [t for t in txs if t.date.date() < date_type.today()]
    assert len(past) >= 2
    assert len({t.unit_price for t in past}) >= 1
    for t in past:
        assert t.unit_price == 100.0 + t.date.day


def test_ticker_on_transfer_recurrence_needs_investment_destination(client, db_session: Session):
    main, livret = accounts(db_session)
    broker = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(broker)
    db_session.commit()
    base = {"account_id": main.id, "name": "DCA", "type": "Sortie", "amount": 400, "frequency": "monthly",
            "day_of_month": 5, "start_date": "2099-01-01T00:00:00", "ticker": "CW8.PA"}
    assert client.post("/recurring-transactions/", json={**base, "transfer_to_account_id": livret.id}).status_code == 422
    assert client.post("/recurring-transactions/", json={**base, "transfer_to_account_id": broker.id}).status_code == 200
