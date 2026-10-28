import asyncio
from datetime import date

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.demo import DEMO_STAMP_KEY, ensure_demo_data, generate_demo_data, is_blocked_in_demo, wipe_database
from app.domain.finance import apply_transaction_to_balance
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.system_setting import SystemSetting
from app.models.transaction import Transaction

TODAY = date(2025, 3, 15)  # jamais « aujourd’hui » : ensure_demo_data doit voir un jeu périmé


def test_demo_data_is_consistent(db_session):
    asyncio.run(generate_demo_data(db_session, today=TODAY))

    accounts = {a.type: a for a in db_session.query(Account).all()}
    assert set(accounts) == {"courant", "epargne", "investissement", "assurance_vie"}

    courant = (
        db_session.query(Transaction)
        .filter(Transaction.account_id == accounts["courant"].id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )
    assert len(courant) > 300
    assert courant[0].type == "Solde Initial"
    assert all(tx.amount > 0 for tx in courant)
    assert max(tx.date.date() for tx in courant) <= TODAY
    balance = 0.0
    for tx in courant:
        balance = apply_transaction_to_balance(balance, tx.type, tx.amount)
        assert tx.running_balance == pytest.approx(balance)
    assert balance > 0

    # Virements internes liés des deux côtés, versements PEA liés à une opération d'investissement
    transfers = [tx for tx in courant if tx.is_transfer]
    assert transfers and all(tx.linked_transaction_id or tx.linked_investment_transaction_id for tx in transfers)
    versements = db_session.query(InvestmentTransaction).filter(InvestmentTransaction.type == "versement").all()
    assert sum(1 for v in versements if v.linked_transaction_id) == len(versements) - 1  # sauf le versement initial

    holdings = {h.ticker: h for h in db_session.query(PortfolioHolding).all()}
    assert {"CW8.PA", "TTE.PA"} <= set(holdings)
    assert all(h.quantity > 0 and h.buy_price_avg for h in holdings.values())
    assert db_session.get(SystemSetting, DEMO_STAMP_KEY).value == TODAY.isoformat()


def test_demo_regeneration(db_session):
    def snapshot():
        return [(t.date, t.merchant, t.amount) for t in db_session.query(Transaction).order_by(Transaction.id).all()]

    asyncio.run(generate_demo_data(db_session, today=TODAY))
    first = snapshot()
    wipe_database(db_session)
    asyncio.run(generate_demo_data(db_session, today=TODAY))
    assert snapshot() == first  # graine fixe : même jour, mêmes données

    # Jeu daté d'un autre jour → effacé et régénéré, sans doublons ; puis plus rien à faire aujourd'hui
    assert asyncio.run(ensure_demo_data(db_session)) is True
    assert db_session.query(Account).count() == 4
    assert asyncio.run(ensure_demo_data(db_session)) is False


@pytest.mark.parametrize(
    "method, path, blocked",
    [
        ("GET", "/admin/profile", False),
        ("PUT", "/admin/profile", True),
        ("POST", "/admin/mcp-tokens", True),
        ("POST", "/admin/reset-database", True),
        ("POST", "/auth/token", False),
        ("POST", "/auth/totp/setup", True),
        ("POST", "/auth/totp/login", False),
        ("POST", "/auth/passkey/register/options", True),
        ("POST", "/auth/passkey/login/options", False),
        ("PUT", "/notifications/settings", True),
        ("POST", "/logos/from-domain", True),
        ("POST", "/etf-profiles/3/refresh", True),
        ("POST", "/transactions", False),
        ("DELETE", "/transactions/12", False),
    ],
)
def test_demo_guard_rules(method, path, blocked):
    assert is_blocked_in_demo(method, path) is blocked


def test_demo_guard_middleware(client, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    response = client.put("/admin/profile", json={"username": "x"})
    assert response.status_code == 403
    assert "démonstration" in response.json()["detail"]
    assert client.get("/health").json() == {"status": "ok", "demo": True}


def test_demo_mode_requires_dedicated_database():
    with pytest.raises(ValidationError):
        Settings(DEMO_MODE=True, app_env="test", database_url="sqlite:///./data/suivi_budget.db")
    assert Settings(DEMO_MODE=True, app_env="test", database_url="sqlite:///./data/demo.db").DEMO_MODE
