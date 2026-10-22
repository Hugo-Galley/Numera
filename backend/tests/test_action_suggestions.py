from datetime import datetime, timedelta

from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction


def _setup(db):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    food = Category(name="Nourriture", type="depense")
    leisure = Category(name="Loisirs", type="depense")
    db.add_all([acc, food, leisure])
    db.commit()
    return acc, food, leisure


def _tx(db, acc, merchant, category=None, days_ago=10, **extra):
    date = datetime.now() - timedelta(days=days_ago)
    db.add(Transaction(
        account_id=acc.id, date=date, month_label=month_label_from_date(date), type="Sortie", merchant=merchant,
        amount=5.0, original_amount=5.0, currency="EUR", running_balance=0.0,
        category_id=category.id if category else None, **extra,
    ))


def _actions(client, prefix):
    return [a for a in client.get("/analytics/actions").json()["actions"] if a["id"].startswith(prefix)]


def test_no_rule_suggested_when_every_transaction_is_already_categorized(client, db_session):
    """22 suggestions en prod, surtout pour des marchands déjà entièrement catégorisés."""
    acc, food, _ = _setup(db_session)
    for i in range(6):
        _tx(db_session, acc, "Machine a café", food, days_ago=i + 1)
    db_session.commit()
    assert _actions(client, "suggest-rule-") == []


def test_rule_suggested_for_uncategorized_transactions_with_the_usual_category(client, db_session):
    acc, food, leisure = _setup(db_session)
    for i in range(4):
        _tx(db_session, acc, "Bowling", leisure, days_ago=i + 1)
    _tx(db_session, acc, "Bowling", food, days_ago=6)
    _tx(db_session, acc, "Bowling", None, days_ago=7)
    db_session.commit()

    [action] = _actions(client, "suggest-rule-")
    assert action["metadata"]["merchant"] == "Bowling"
    assert action["metadata"]["suggested_category_id"] == leisure.id  # la plus fréquente, pas l'id le plus grand
    assert "1 transaction(s) sans catégorie" in action["description"]


def test_recurring_transactions_do_not_trigger_rule_suggestions(client, db_session):
    acc, _, _ = _setup(db_session)
    rd = RecurringTransaction(account_id=acc.id, name="Spotify", type="Sortie", amount=7.0, currency="EUR",
                              frequency="monthly", day_of_month=1, start_date=datetime(2026, 1, 1))
    db_session.add(rd)
    db_session.commit()
    for i in range(6):
        _tx(db_session, acc, "Spotify", None, days_ago=i * 20 + 1, recurring_transaction_id=rd.id)
    db_session.commit()
    assert _actions(client, "suggest-rule-") == []


def test_normalization_only_suggested_for_several_spellings_of_one_merchant(client, db_session):
    acc, food, _ = _setup(db_session)
    for i in range(12):
        _tx(db_session, acc, "Navigo", food, days_ago=i + 1)
    for i in range(10):
        _tx(db_session, acc, "Machine a café", food, days_ago=i + 1)
    _tx(db_session, acc, "MACHINE A CAFE 0412", food)
    db_session.commit()

    [action] = _actions(client, "suggest-normalization-")
    assert action["metadata"]["merchant"] == "Machine a café"
    assert sorted(action["metadata"]["variants"]) == ["MACHINE A CAFE 0412", "Machine a café"]
    assert action["metadata"]["count"] == 11
