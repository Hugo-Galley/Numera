"""Nom lisible du titre d'une récurrence d'investissement (aperçu du parcours de l'argent)."""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.models.recurring_transaction import RecurringTransaction


def _rule(db: Session, account_id: int, ticker: str | None, **kw) -> RecurringTransaction:
    rule = RecurringTransaction(
        account_id=account_id, name=f"DCA {ticker}", type="versement", amount=100.0, currency="EUR",
        frequency="monthly", day_of_month=5, start_date=datetime(2030, 1, 1), is_active=True,
        auto_generate=False, ticker=ticker, **kw,
    )
    db.add(rule)
    return rule


def test_security_name_from_etf_profile_then_holding(client: TestClient, db_session: Session, measure_queries):
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(pea)
    db_session.flush()
    profile = EtfProfile(name="MSCI World", ticker="CW8.PA")
    db_session.add(profile)
    db_session.add(PortfolioHolding(account_id=pea.id, ticker="AI.PA", asset_name="Air Liquide", quantity=1))
    _rule(db_session, pea.id, "CW8.PA")
    _rule(db_session, pea.id, "AI.PA")
    _rule(db_session, pea.id, "XYZ")
    _rule(db_session, pea.id, None)
    db_session.flush()
    _rule(db_session, pea.id, "OTHER", etf_profile_id=profile.id)
    db_session.commit()

    res, first = measure_queries(lambda: client.get("/recurring-transactions/"))
    assert res.status_code == 200, res.text
    names = {r["ticker"]: r["security_name"] for r in res.json()}
    assert names == {"CW8.PA": "MSCI World", "AI.PA": "Air Liquide", "XYZ": None, None: None, "OTHER": "MSCI World"}

    for i in range(5):
        _rule(db_session, pea.id, f"T{i}")
    db_session.commit()
    _, count = measure_queries(lambda: client.get("/recurring-transactions/"))
    assert count == first  # pas de requête par règle


def test_security_name_in_create_response(client: TestClient, db_session: Session):
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add_all([pea, EtfProfile(name="S&P 500", ticker="ESE.PA")])
    db_session.commit()
    res = client.post("/recurring-transactions/", json={
        "account_id": pea.id, "name": "DCA", "type": "versement", "amount": 100.0, "currency": "EUR",
        "frequency": "monthly", "day_of_month": 5, "start_date": "2030-01-01T00:00:00",
        "is_active": True, "auto_generate": False, "ticker": "ESE.PA",
    })
    assert res.status_code == 200, res.text
    assert res.json()["security_name"] == "S&P 500"
