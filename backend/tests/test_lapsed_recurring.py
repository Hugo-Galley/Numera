"""Récurrences actives mais plus prélevées, échéance annuelle et virements internes dans la projection."""
from datetime import datetime, timedelta

from app.core.finance import is_lapsed, month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction


def _setup(db):
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    livret = Account(name="Livret A", type="epargne", currency="EUR", active=True)
    subs = Category(name="Abonnement", type="depense")
    db.add_all([courant, livret, subs])
    db.commit()
    return courant, livret, subs


def _recurring(db, account, name, amount, subs, frequency="monthly", **extra):
    rd = RecurringTransaction(
        account_id=account.id, name=name, type="Sortie", amount=amount, currency="EUR", category_id=subs.id,
        frequency=frequency, day_of_month=extra.pop("day_of_month", 5),
        start_date=extra.pop("start_date", datetime.now() - timedelta(days=400)),
        is_active=True, auto_generate=False, **extra,
    )
    db.add(rd)
    db.commit()
    return rd


def _paid(db, account, rd, when):
    db.add(Transaction(
        account_id=account.id, date=when, month_label=month_label_from_date(when), type="Sortie",
        merchant=rd.name, amount=rd.amount, original_amount=rd.amount, currency="EUR",
        running_balance=0.0, recurring_transaction_id=rd.id, category_id=rd.category_id,
    ))
    db.commit()


def test_is_lapsed_needs_two_missed_periods():
    today = datetime(2026, 10, 26)
    assert is_lapsed("monthly", datetime(2026, 6, 4), today)
    assert not is_lapsed("monthly", datetime(2026, 9, 1), today)
    assert not is_lapsed("monthly", None, today)  # jamais rattachée : on ne conclut rien
    assert not is_lapsed("yearly", datetime(2026, 1, 1), today)


def test_lapsed_subscription_is_flagged_and_left_out_of_totals(client, db_session):
    courant, _, subs = _setup(db_session)
    navigo = _recurring(db_session, courant, "Navigo", 42.7, subs)
    spotify = _recurring(db_session, courant, "Spotify", 7.07, subs)
    _paid(db_session, courant, navigo, datetime.now() - timedelta(days=140))
    _paid(db_session, courant, spotify, datetime.now() - timedelta(days=20))

    data = client.get("/analytics/subscriptions").json()
    by_name = {s["name"]: s for s in data["subscriptions"]}

    assert by_name["Navigo"]["status"] == "lapsed"
    assert by_name["Navigo"]["counts_in_total"] is False
    assert by_name["Spotify"]["status"] == "active"
    assert data["total_monthly"] == 7.07


def test_yearly_subscription_has_a_next_occurrence(client, db_session):
    courant, _, subs = _setup(db_session)
    start = datetime.now() - timedelta(days=60)
    _recurring(db_session, courant, "Yazio", 21.9, subs, frequency="yearly", start_date=start, day_of_month=start.day)

    data = client.get("/analytics/subscriptions").json()

    assert data["subscriptions"][0]["next_occurrence"] is not None


def test_projection_ignores_internal_transfers_and_lapsed(client, db_session):
    courant, livret, subs = _setup(db_session)
    now = datetime.now()
    for acc, balance in ((courant, 1000.0), (livret, 5000.0)):
        db_session.add(Transaction(
            account_id=acc.id, date=now - timedelta(days=1), month_label=month_label_from_date(now),
            type="Solde Initial", merchant="Initial", amount=balance, original_amount=balance,
            currency="EUR", running_balance=balance,
        ))
    db_session.commit()
    day = (now + timedelta(days=3)).day
    _recurring(db_session, courant, "Alimentation Livret A", 150.0, subs, day_of_month=day, transfer_to_account_id=livret.id)
    navigo = _recurring(db_session, courant, "Navigo", 42.7, subs, day_of_month=day)
    _paid(db_session, courant, navigo, now - timedelta(days=140))

    data = client.get("/analytics/cashflow-projection", params={"days": 30}).json()

    # Ni le virement vers le livret (déjà compté dans le solde), ni l'abonnement arrêté
    assert data["current_balance"] == 6000.0
    assert data["projected_balance"] == 6000.0
    assert data["events"] == []
