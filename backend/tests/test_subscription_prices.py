from datetime import datetime, timedelta

from app.domain.finance import month_label_from_date
from app.services.subscription_prices import detect_price_changes
from app.models.account import Account
from app.models.transaction import Transaction

NOW = datetime(2026, 10, 26)


def _account(db, currency="EUR"):
    acc = Account(name="Principal", type="courant", currency=currency, active=True)
    db.add(acc)
    db.commit()
    return acc


def _series(db, account, merchant, amounts, step_days=30, end=NOW - timedelta(days=5)):
    """Prélèvements réguliers, le dernier montant de `amounts` à la date `end`."""
    for i, amount in enumerate(amounts):
        date = end - timedelta(days=step_days * (len(amounts) - 1 - i))
        db.add(Transaction(
            account_id=account.id, date=date, month_label=month_label_from_date(date), type="Sortie",
            merchant=merchant, amount=amount, original_amount=amount, currency=account.currency, running_balance=0.0,
        ))
    db.commit()


def test_monthly_increase_is_detected(db_session):
    acc = _account(db_session)
    _series(db_session, acc, "NETFLIX.COM", [13.49, 13.49, 13.49, 15.99])
    [change] = detect_price_changes(db_session, now=NOW)
    assert (change.old_amount, change.new_amount) == (13.49, 15.99)
    assert change.frequency == "monthly"
    assert change.delta == 2.5 and change.annual_impact == 30.0


def test_increase_stays_flagged_while_new_price_continues(db_session):
    acc = _account(db_session)
    _series(db_session, acc, "Spotify", [10.99, 10.99, 10.99, 11.99, 11.99, 11.99])
    [change] = detect_price_changes(db_session, now=NOW)
    assert change.changed_on == (NOW - timedelta(days=5 + 60)).date()


def test_old_increase_is_no_longer_flagged(db_session):
    acc = _account(db_session)
    _series(db_session, acc, "Spotify", [10.99] * 3 + [11.99] * 9)
    assert detect_price_changes(db_session, now=NOW) == []


def test_decrease_and_stable_price_are_ignored(db_session):
    acc = _account(db_session)
    _series(db_session, acc, "Free Mobile", [19.99, 19.99, 19.99, 15.99])
    _series(db_session, acc, "Assurance", [42.0, 42.0, 42.0, 42.0])
    assert detect_price_changes(db_session, now=NOW) == []


def test_variable_amounts_are_not_a_price_change(db_session):
    acc = _account(db_session)
    _series(db_session, acc, "EDF", [60.0, 75.0, 52.0, 90.0])
    assert detect_price_changes(db_session, now=NOW) == []


def test_irregular_purchases_are_ignored(db_session):
    acc = _account(db_session)
    _series(db_session, acc, "Carrefour", [20.0, 20.0, 20.0, 35.0], step_days=4)
    assert detect_price_changes(db_session, now=NOW) == []


def test_yearly_increase_needs_one_previous_payment(db_session):
    acc = _account(db_session)
    _series(db_session, acc, "Assurance habitation", [180.0, 195.0], step_days=365)
    [change] = detect_price_changes(db_session, now=NOW)
    assert change.frequency == "yearly" and change.annual_impact == 15.0


def test_stopped_subscription_is_ignored(db_session):
    acc = _account(db_session)
    _series(db_session, acc, "Deezer", [9.99, 9.99, 9.99, 10.99], end=NOW - timedelta(days=120))
    assert detect_price_changes(db_session, now=NOW) == []


def test_ignored_and_transfer_lines_are_excluded(db_session):
    acc = _account(db_session)
    _series(db_session, acc, "Netflix", [13.49, 13.49, 13.49, 15.99])
    db_session.query(Transaction).update({"is_subscription_ignored": True})
    db_session.commit()
    assert detect_price_changes(db_session, now=NOW) == []


def test_price_change_reaches_subscriptions_and_action_center(client, db_session):
    acc = _account(db_session)
    now = datetime.now()
    _series(db_session, acc, "Netflix", [13.49, 13.49, 13.49, 15.99], end=now - timedelta(days=2))

    subs = client.get("/analytics/subscriptions").json()
    [change] = subs["price_changes"]
    assert change["name"] == "Netflix" and change["delta"] == 2.5

    actions = client.get("/analytics/actions").json()["actions"]
    assert any(a["id"] == change["id"] and a["type"] == "subscription" for a in actions)

    client.post("/analytics/actions/dismiss", json={"id": change["id"]})
    actions = client.get("/analytics/actions").json()["actions"]
    assert all(a["id"] != change["id"] for a in actions)
