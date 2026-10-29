from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.services.budget import reimbursements as remb
from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


def _tx(db, account, type_, amount, date, merchant, category=None):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_, merchant=merchant,
        amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
        category_id=category.id if category else None,
    )
    db.add(t)
    db.commit()
    return t


@pytest.fixture()
def scenario(db_session: Session):
    main = Account(name="Principal", type="courant", currency="EUR", active=True)
    resto_cat = Category(name="Restaurants", type="depense")
    remb_cat = Category(name="Remboursement (recu)", type="revenu")
    db_session.add_all([main, resto_cat, remb_cat])
    db_session.commit()
    sortie = _tx(db_session, main, "Sortie", 90.0, datetime(2025, 9, 28), "RESTO", resto_cat)
    entree = _tx(db_session, main, "Entree", 30.0, datetime(2025, 10, 3), "VIR DENIS", remb_cat)
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    remb.create_claim(db_session, sortie.id, "Julie", 30.0)
    remb.allocate(db_session, claim, entree.id)
    return main, sortie, entree


def test_budget_is_net_on_expense_month(client, scenario):
    sept = client.get("/analytics/budget", params={"month": 9, "year": 2025}).json()
    octo = client.get("/analytics/budget", params={"month": 10, "year": 2025}).json()
    assert sept["depenses_totales"] == 60.0
    assert octo["revenus_totaux"] == 0.0


def test_expenses_by_category_and_top_merchants_are_net(client, scenario):
    cats = client.get("/analytics/expenses-by-category", params={"month": 9, "year": 2025}).json()
    assert {i["category"]["name"]: i["total"] for i in cats["items"]}["Restaurants"] == 60.0
    top = client.get("/analytics/top-merchants", params={"month": 9, "year": 2025}).json()
    assert {i["merchant"]: i["total"] for i in top["items"]}["RESTO"] == 60.0


def test_timeseries_and_money_flow_are_net(client, scenario):
    flows = {f["month"]: f for f in client.get("/analytics/timeseries", params={"year": 2025}).json()["monthly_flows"]}
    assert flows[9]["expense"] == 60.0
    assert flows.get(10, {"income": 0.0})["income"] == 0.0  # un mois sans flux est omis
    sept = client.get("/analytics/money-flow", params={"month": 9, "year": 2025}).json()
    assert sept["fixed_charges"]["amount"] + sept["variable_expenses"]["amount"] == 60.0
    assert client.get("/analytics/money-flow", params={"month": 10, "year": 2025}).json()["income"] == 0.0


def test_raw_cash_endpoints_are_unchanged(client, scenario):
    main, _, _ = scenario
    flow = client.get("/analytics/account-flow-summary", params={"account_id": main.id}).json()
    assert flow["avg_expense"] == 90.0


def test_partial_allocation_counts_remainder_as_income(client, db_session, scenario):
    main, sortie, _ = scenario
    big = _tx(db_session, main, "Entree", 50.0, datetime(2025, 10, 10), "VIR JULIE")
    db_session.refresh(sortie)
    julie = next(c for c in sortie.claims if c.debtor == "Julie")
    remb.allocate(db_session, julie, big.id)  # 30 affectés, 20 restent un revenu
    octo = client.get("/analytics/budget", params={"month": 10, "year": 2025}).json()
    assert octo["revenus_totaux"] == 20.0
    sept = client.get("/analytics/budget", params={"month": 9, "year": 2025}).json()
    assert sept["depenses_totales"] == 30.0


def test_audit_flags_unallocated_reimbursements(client, db_session, scenario):
    from app.core.time import utcnow_naive
    main, _, _ = scenario
    cat = db_session.query(Category).filter(Category.name == "Remboursement (recu)").one()
    cpam = _tx(db_session, main, "Entree", 12.0, utcnow_naive(), "CPAM", cat)
    issues = {i["id"]: i for i in client.get("/analytics/audit").json()["issues"]}
    assert issues["unallocated-reimbursements"]["count"] == 1
    assert issues["unallocated-reimbursements"]["action_url"] == "/reimbursements"
    details = client.get("/analytics/audit/unallocated-reimbursements").json()
    assert [t["id"] for t in details["transactions"]] == [cpam.id]


def test_audit_silent_without_open_claim(client, db_session):
    from app.core.time import utcnow_naive
    main = Account(name="P", type="courant", currency="EUR", active=True)
    cat = Category(name="Remboursement (recu)", type="revenu")
    db_session.add_all([main, cat])
    db_session.commit()
    _tx(db_session, main, "Entree", 12.0, utcnow_naive(), "CPAM", cat)
    ids = {i["id"] for i in client.get("/analytics/audit").json()["issues"]}
    assert "unallocated-reimbursements" not in ids


def test_action_center_lists_unallocated_reimbursements(client, db_session, scenario):
    from app.core.time import utcnow_naive
    main, _, _ = scenario
    cat = db_session.query(Category).filter(Category.name == "Remboursement (recu)").one()
    _tx(db_session, main, "Entree", 12.0, utcnow_naive(), "CPAM", cat)
    actions = {a["id"]: a for a in client.get("/analytics/actions").json()["actions"]}
    action = actions["unallocated-reimbursements"]
    assert action["action_type"] == "link" and action["action_url"] == "/reimbursements"
