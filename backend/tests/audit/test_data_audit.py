from datetime import datetime

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


def _tx(account_id: int, date: datetime, merchant: str, amount: float, category_id: int | None = None):
    return Transaction(
        account_id=account_id,
        date=date,
        month_label=date.strftime("%b %Y"),
        type="Sortie",
        merchant=merchant,
        category_id=category_id,
        amount=amount,
        original_amount=amount,
        currency="EUR",
        running_balance=1000.0 - amount,
    )


def test_data_audit_detects_actionable_issues(client, db_session):
    checking = Account(name="Checking", type="courant", currency="EUR", active=True)
    broker = Account(name="Broker", type="investissement", currency="EUR", active=True)
    used_category = Category(name="Courses", type="depense")
    unused_category = Category(name="Unused", type="depense")
    db_session.add_all([checking, broker, used_category, unused_category])
    db_session.commit()

    duplicate_date = datetime(2026, 6, 10, 9, 0)
    db_session.add_all([
        _tx(checking.id, datetime(2026, 6, 8), "Mystery", 42.0),
        _tx(checking.id, duplicate_date, "Supermarket", 18.0, used_category.id),
        _tx(checking.id, duplicate_date, "Supermarket", 18.0, used_category.id),
        _tx(checking.id, datetime(2026, 6, 11), "", 9.5, used_category.id),
    ])
    db_session.commit()

    response = client.get("/analytics/audit")

    assert response.status_code == 200
    data = response.json()
    issue_ids = {issue["id"] for issue in data["issues"]}

    assert "uncategorized-expenses" in issue_ids
    assert "duplicate-transactions" in issue_ids
    assert "missing-merchants" in issue_ids
    assert "missing-initial-balances" in issue_ids
    assert "stale-investment-snapshots" in issue_ids
    assert "unused-categories" in issue_ids
    assert data["summary"]["high_count"] == 2
    assert data["summary"]["total_transactions"] == 4
