from datetime import datetime

from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction

DAY = datetime(2025, 10, 10)


def test_investment_account_detail_exposes_security_fields(client, db_session):
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(pea)
    db_session.commit()
    buy = InvestmentTransaction(
        account_id=pea.id, date=DAY, type="achat", amount=1005.0, original_amount=1005.0, currency="EUR",
        ticker="CW8", isin="LU1681043599", quantity=10.0, unit_price=100.0, fees=5.0,
    )
    div = InvestmentTransaction(
        account_id=pea.id, date=DAY, type="dividende", amount=50.0, original_amount=50.0, currency="EUR",
        ticker="CW8", withholding_tax=7.5, reinvested=True,
    )
    db_session.add_all([buy, div])
    db_session.commit()
    db_session.refresh(buy)
    db_session.refresh(div)
    div_id, buy_id = div.id, buy.id
    div_row_db = db_session.get(InvestmentTransaction, div_id)
    div_row_db.reinvest_of_id = buy_id
    db_session.commit()

    rows = {r["id"]: r for r in client.get(f"/analytics/investments/{pea.id}").json()["transactions"]}

    assert rows[buy_id]["ticker"] == "CW8"
    assert rows[buy_id]["isin"] == "LU1681043599"
    assert rows[buy_id]["quantity"] == 10.0
    assert rows[buy_id]["unit_price"] == 100.0
    assert rows[buy_id]["fees"] == 5.0
    assert rows[div_id]["withholding_tax"] == 7.5
    assert rows[div_id]["reinvested"] is True
    assert rows[div_id]["reinvest_of_id"] == buy_id
