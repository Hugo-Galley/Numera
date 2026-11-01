"""Audit des données : appariement des virements internes sans une requête par sortie."""
from datetime import datetime, timedelta

from sqlalchemy import event

from app.models.account import Account
from app.models.transaction import Transaction

NOW = datetime.now()


def _tx(account_id: int, date: datetime, kind: str, amount: float, currency: str = "EUR") -> Transaction:
    return Transaction(
        account_id=account_id, date=date, month_label=date.strftime("%Y-%m"), type=kind, merchant="Virement",
        amount=amount, original_amount=amount, currency=currency, running_balance=0.0,
    )


def _accounts(db_session):
    a = Account(name="Courant", type="courant", currency="EUR", active=True)
    b = Account(name="Livret", type="epargne", currency="EUR", active=True)
    db_session.add_all([a, b])
    db_session.flush()
    return a, b


def _count_queries(db_session, call):
    statements = []

    def listener(conn, cursor, statement, params, context, executemany):
        statements.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", listener)
    try:
        response = call()
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    return response, len(statements)


def test_audit_pairs_transfers_in_constant_number_of_queries(client, db_session):
    courant, livret = _accounts(db_session)
    for i in range(40):
        day = NOW - timedelta(days=5 + i)
        db_session.add(_tx(courant.id, day, "Sortie", 100.0 + i))
        db_session.add(_tx(livret.id, day + timedelta(days=1), "Entree", 100.0 + i))
    db_session.commit()

    response, queries = _count_queries(db_session, lambda: client.get("/analytics/audit"))

    issue = next(i for i in response.json()["issues"] if i["id"] == "unmatched-transfers")
    assert issue["count"] == 40
    assert len(issue["samples"]) == 5
    assert queries < 40, f"{queries} requêtes SQL : une par sortie"


def test_audit_ignores_other_currency_same_account_and_distant_dates(client, db_session):
    courant, livret = _accounts(db_session)
    day = NOW - timedelta(days=10)
    db_session.add_all([
        _tx(courant.id, day, "Sortie", 50.0),
        _tx(livret.id, day, "Entree", 50.0, currency="USD"),             # autre devise
        _tx(courant.id, day, "Entree", 50.0),                            # même compte
        _tx(livret.id, day + timedelta(days=4), "Entree", 50.0),         # hors fenêtre ±3 j
    ])
    db_session.commit()

    response = client.get("/analytics/audit")

    assert all(i["id"] != "unmatched-transfers" for i in response.json()["issues"])


def test_audit_pair_details_list_up_to_five_matches_by_date_then_id(client, db_session):
    courant, livret = _accounts(db_session)
    day = NOW - timedelta(days=10)
    db_session.add(_tx(courant.id, day, "Sortie", 75.0))
    for offset in (3, 2, 1, 0, -1, -2, -3):
        db_session.add(_tx(livret.id, day + timedelta(days=offset), "Entree", 75.0))
    db_session.commit()

    response = client.get("/analytics/audit/unmatched-transfers")

    assert response.status_code == 200
    pairs = response.json()["transfer_pairs"]
    dates = [p["entree"]["date"] for p in pairs]
    assert len(pairs) == 5
    assert dates == sorted(dates)
