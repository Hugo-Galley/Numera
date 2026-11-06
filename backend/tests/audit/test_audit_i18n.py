"""Centre d'Actions et audit des données dans la langue de l'interface (Accept-Language)."""
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from app.core.i18n import set_language
from app.domain.audit import month_name
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.audit import context as audit_context
from app.services.audit.rules import backups, budget, subscription_prices

EN = {"Accept-Language": "en"}


@pytest.fixture(autouse=True)
def _reset_language():
    set_language("fr")
    yield
    set_language("fr")


def _tx(account_id, when, merchant, amount, category_id=None):
    return Transaction(
        account_id=account_id, date=when, month_label=when.strftime("%b %Y"), type="Sortie", merchant=merchant,
        category_id=category_id, amount=amount, original_amount=amount, currency="EUR", running_balance=1000.0 - amount,
    )


@pytest.fixture
def seeded(db_session):
    checking = Account(name="Checking", type="courant", currency="EUR", active=True)
    broker = Account(name="Broker", type="investissement", currency="EUR", active=True)
    cat = Category(name="Courses", type="depense")
    db_session.add_all([checking, broker, cat, Category(name="Unused", type="depense")])
    db_session.commit()
    same = datetime(2026, 6, 10, 9, 0)
    db_session.add_all([
        _tx(checking.id, datetime(2026, 6, 8), "Mystery", 42.0),
        _tx(checking.id, same, "Supermarket", 18.0, cat.id),
        _tx(checking.id, same, "Supermarket", 18.0, cat.id),
    ])
    db_session.commit()


def _by_id(items):
    return {i["id"]: i for i in items}


def test_action_center_in_english(client, seeded):
    fr = _by_id(client.get("/analytics/actions").json()["actions"])
    en = _by_id(client.get("/analytics/actions", headers=EN).json()["actions"])
    assert fr["uncategorized-expenses"]["title"] == "Transactions sans catégorie"
    assert en["uncategorized-expenses"]["title"] == "Transactions without a category"
    assert en["uncategorized-expenses"]["description"] == "You have 1 expense without a category."
    assert en["uncategorized-expenses"]["action_label"] == "Categorize"
    assert en["duplicate-transactions"]["title"] == "Suspected duplicates"
    assert en["duplicate-transactions"]["description"] == "2 transactions look like duplicates."
    assert en["stale-snapshots"]["title"] == "Outdated investment balances"
    assert en["stale-snapshots"]["description"] == "1 investment account has no recent update."
    # les identifiants, eux, ne dépendent jamais de la langue (un insight écarté le reste)
    assert set(fr) == set(en)


def test_data_audit_in_english(client, seeded):
    fr = _by_id(client.get("/analytics/audit").json()["issues"])
    en = _by_id(client.get("/analytics/audit", headers=EN).json()["issues"])
    assert fr["duplicate-transactions"]["title"] == "Doublons suspects"
    assert en["duplicate-transactions"]["title"] == "Suspected duplicates"
    assert en["uncategorized-expenses"]["title"] == "Transactions without a category"
    assert en["missing-initial-balances"]["title"] == "Accounts without an opening balance"
    assert en["unused-categories"]["action_label"] == "Archive or delete"
    assert set(fr) == set(en)


def test_month_names_follow_language():
    assert month_name("2026-10") == "octobre 2026"
    set_language("en")
    assert month_name("2026-10") == "October 2026"


def test_budget_alerts_in_english(monkeypatch, db_session):
    alert = SimpleNamespace(category_id=3, category_name="Courses", monthly_spent=120.5, monthly_limit=100.0, monthly_ratio=1.2)
    near = SimpleNamespace(category_id=4, category_name="Sorties", monthly_spent=90.0, monthly_limit=100.0, monthly_ratio=0.9)

    async def fake(**_):
        return [alert, near]

    monkeypatch.setattr(budget, "compute_budget_alerts", fake)
    ctx = audit_context.AuditContext(db=db_session, now=datetime(2026, 6, 15))
    import asyncio

    set_language("en")
    over, close = asyncio.run(budget.detect(ctx))
    assert over.title == "Budget exceeded: Courses"
    assert over.description == "You spent €120.5 against a limit of €100.0."
    assert over.action_label == "View details"
    assert close.title == "Budget almost reached: Sorties"
    assert close.description == "You are at 90% of your limit for Sorties."


def test_backup_alert_in_english(monkeypatch, db_session):
    last = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)
    monkeypatch.setattr(backups, "backup_status", lambda: {"configured": True, "stale": True, "last_error": "disk full", "last_backup_at": last})
    ctx = audit_context.AuditContext(db=db_session, now=datetime(2026, 6, 15))
    set_language("en")
    (item,) = backups.detect(ctx)
    assert item.title == "Backup overdue"
    assert item.description.startswith("Last successful backup: ")
    assert item.description.endswith("Last error: disk full")
    assert item.action_label == "View backups"


def test_subscription_price_alert_in_english(monkeypatch, db_session):
    change = SimpleNamespace(
        name="Netflix", account_id=1, currency="EUR", frequency="monthly", old_amount=10.0, new_amount=12.0,
        changed_on=date(2026, 5, 3), delta_pct=20.0, annual_impact=24.0, key="k",
    )
    monkeypatch.setattr(subscription_prices, "detect_price_changes", lambda db: [change])
    monkeypatch.setattr(subscription_prices, "price_change_id", lambda c: "sub-1")
    ctx = audit_context.AuditContext(db=db_session, now=datetime(2026, 6, 15))
    set_language("en")
    (item,) = subscription_prices.detect(ctx)
    assert item.title == "Price increase: Netflix"
    assert item.description == "Went from 10.00 to 12.00 EUR per month on 03/05/2026 (+20.0%), i.e. 24.00 EUR more per year. Still worth it at this price?"
