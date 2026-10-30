from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.recurring_transaction import RecurringTransaction
from app.models.salary_config import SalaryConfig
from app.models.transaction import Transaction
from app.services.budget.balances import recalculate_running_balances


def _tx(db: Session, account: Account, when: datetime, tx_type: str, amount: float, merchant: str, **kw) -> Transaction:
    tx = Transaction(
        account_id=account.id,
        date=when,
        month_label=month_label_from_date(when),
        type=tx_type,
        merchant=merchant,
        amount=amount,
        original_amount=amount,
        currency="EUR",
        running_balance=0.0,
        **kw,
    )
    db.add(tx)
    return tx


@pytest.fixture
def setup(db_session: Session) -> dict:
    db = db_session
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    food = Category(name="Courses", type="depense")
    rent = Category(name="Logement", type="depense")
    subs = Category(name="Abonnement", type="depense")
    epargne = Category(name="Epargne", type="depense")
    db.add_all([courant, food, rent, subs, epargne])
    db.commit()

    netflix = RecurringTransaction(
        account_id=courant.id, name="Netflix", type="Sortie", amount=15.0, currency="EUR",
        category_id=subs.id, frequency="monthly", start_date=datetime(2024, 1, 5), is_active=True,
    )
    gym = RecurringTransaction(
        account_id=courant.id, name="Salle de sport", type="Sortie", amount=40.0, currency="EUR",
        category_id=subs.id, frequency="monthly", start_date=datetime(2024, 1, 5), is_active=False,
    )
    db.add_all([netflix, gym])
    db.commit()

    _tx(db, courant, datetime(2024, 1, 1), "Solde Initial", 1000.0, "Solde")
    for month in range(1, 13):
        _tx(db, courant, datetime(2024, month, 25), "Entree", 2000.0, "Salaire")
        _tx(db, courant, datetime(2024, month, 3), "Sortie", 800.0, "Loyer", category_id=rent.id)
        _tx(db, courant, datetime(2024, month, 6), "Sortie", 40.0, "Salle de sport", category_id=subs.id, recurring_transaction_id=gym.id)
        _tx(db, courant, datetime(2025, month, 25), "Entree", 2500.0, "Salaire")
        _tx(db, courant, datetime(2025, month, 3), "Sortie", 800.0, "Loyer", category_id=rent.id)
        _tx(db, courant, datetime(2025, month, 10), "Sortie", 300.0 if month != 8 else 900.0, "Carrefour", category_id=food.id)
        _tx(db, courant, datetime(2025, month, 5), "Sortie", 15.0, "Netflix", category_id=subs.id, recurring_transaction_id=netflix.id)
        _tx(db, courant, datetime(2025, month, 28), "Sortie", 200.0, "Livret", category_id=epargne.id)
    db.commit()
    recalculate_running_balances(db, courant.id)
    db.add(SalaryConfig(salary_account_id=courant.id, net_salary=2180.0))
    db.commit()
    return {"courant": courant}


def test_wrapped_totals_match_monthly_budget(client: TestClient, setup):
    res = client.get("/analytics/wrapped", params={"year": 2025})
    assert res.status_code == 200
    data = res.json()
    totals = data["totals"]

    assert data["has_data"] is True
    assert data["is_partial"] is False
    assert data["available_years"] == [2025, 2024]
    assert totals["income"] == 30000.0
    # Loyer 9600 + courses 300×11 + 900 + Netflix 180 ; l'épargne n'est pas une dépense réelle
    assert totals["real_expenses"] == 9600.0 + 3300.0 + 900.0 + 180.0
    assert totals["saved"] == round(30000.0 - totals["real_expenses"], 2)
    assert totals["savings_rate"] == round(totals["saved"] / 30000.0 * 100, 1)
    assert totals["invested"] == 2400.0
    assert totals["subscriptions_cost"] == 180.0
    assert totals["expense_count"] == 12 * 4

    assert data["most_expensive_month"]["month"] == 8
    assert data["top_categories"][0]["name"] == "Logement"
    assert all(c["name"] != "Epargne" for c in data["top_categories"])
    assert data["top_merchants"][0]["merchant"] == "Loyer"
    assert data["biggest_expense"]["merchant"] == "Carrefour"
    assert data["biggest_expense"]["amount"] == 900.0


def test_wrapped_compares_with_previous_year(client: TestClient, setup):
    data = client.get("/analytics/wrapped", params={"year": 2025}).json()
    prev = data["previous"]
    assert prev["year"] == 2024
    assert prev["totals"]["income"] == 24000.0
    assert prev["income_change_pct"] == 25.0
    assert prev["savings_rate_change_pts"] == round(data["totals"]["savings_rate"] - prev["totals"]["savings_rate"], 1)
    # Patrimoine : fin 2024 → fin 2025 sur le compte courant
    assert data["totals"]["net_worth_start"] == prev["totals"]["net_worth_end"]


def test_wrapped_subscription_changes(client: TestClient, setup):
    data = client.get("/analytics/wrapped", params={"year": 2025}).json()
    assert [s["name"] for s in data["new_subscriptions"]] == ["Netflix"]
    # La salle de sport s'est arrêtée fin 2024 : pas dans le bilan 2025
    assert data["stopped_subscriptions"] == []

    data_2024 = client.get("/analytics/wrapped", params={"year": 2024}).json()
    assert [s["name"] for s in data_2024["stopped_subscriptions"]] == ["Salle de sport"]
    assert data_2024["stopped_subscriptions_yearly_saving"] == 480.0
    assert data_2024["previous"] is None


def test_wrapped_work_hours(client: TestClient, setup):
    data = client.get("/analytics/wrapped", params={"year": 2025}).json()
    rate = round(2180 * 12 / (218 * 7), 2)
    assert data["hourly_rate"] == rate
    assert data["biggest_expense"]["work_hours"] == round(900.0 / rate, 1)


def test_wrapped_empty_and_future_year(client: TestClient):
    data = client.get("/analytics/wrapped", params={"year": 2020}).json()
    assert data["has_data"] is False
    assert data["biggest_expense"] is None
    assert client.get("/analytics/wrapped", params={"year": datetime.now().year + 1}).status_code == 400


def test_wrapped_skips_comparison_with_nearly_empty_previous_year(client: TestClient, db_session: Session):
    """Suivi commencé fin 2024 : comparer 2025 à deux mois de 2024 donnerait des « +1 000 % »."""
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(courant)
    db_session.commit()
    _tx(db_session, courant, datetime(2024, 12, 20), "Interets", 2.0, "Intérêts")
    _tx(db_session, courant, datetime(2024, 12, 21), "Sortie", 10.0, "Café")
    for month in range(1, 13):
        _tx(db_session, courant, datetime(2025, month, 25), "Entree", 2000.0, "Salaire")
        _tx(db_session, courant, datetime(2025, month, 3), "Sortie", 800.0, "Loyer")
    db_session.commit()

    data = client.get("/analytics/wrapped", params={"year": 2025}).json()

    assert 2024 in data["available_years"]
    assert data["previous"] is None
