"""Scanner de diversification : valeur des comptes d'investissement et part hors positions (espèces, fonds euros,
comptes sans position), pour rapprocher le donut des positions du total de la répartition par compte."""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.portfolio_holding import PortfolioHolding


def _accounts(db: Session) -> tuple[Account, Account]:
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    peeg = Account(name="PEEG", type="investissement", currency="EUR", active=True)
    livret = Account(name="Livret A", type="epargne", currency="EUR", active=True)
    db.add_all([pea, peeg, livret])
    db.commit()
    db.add_all([
        BalanceSnapshot(account_id=pea.id, date=datetime(2026, 1, 1), current_value=1200.0),
        BalanceSnapshot(account_id=peeg.id, date=datetime(2026, 1, 1), current_value=300.0),
        BalanceSnapshot(account_id=livret.id, date=datetime(2026, 1, 1), current_value=5000.0),
        PortfolioHolding(account_id=pea.id, ticker="AIR.PA", asset_name="Airbus", quantity=10.0,
                         buy_price_avg=100.0, currency="EUR"),
    ])
    db.commit()
    return pea, peeg


def test_portfolio_totals_include_accounts_value_and_outside_positions(client: TestClient, db_session: Session):
    _accounts(db_session)

    totals = client.get("/analytics/diversity-scanner").json()["totals"]

    assert totals["stocks_eur"] == 1000.0
    # PEA (1 200) + PEEG sans position (300) ; le livret n'est pas un compte d'investissement
    assert totals["accounts_eur"] == 1500.0
    assert totals["outside_positions_eur"] == 500.0


def test_account_totals_are_limited_to_that_account(client: TestClient, db_session: Session):
    pea, _ = _accounts(db_session)

    totals = client.get(f"/analytics/diversity-scanner?account_id={pea.id}").json()["totals"]

    assert totals["accounts_eur"] == 1200.0
    assert totals["outside_positions_eur"] == 200.0
