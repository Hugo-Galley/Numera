"""Suggestions de virements : l'appariement lit des colonnes, seuls les couples trouvés sont chargés en entier."""
from datetime import datetime, timedelta

from sqlalchemy import event

from app.models.account import Account
from app.models.transaction import Transaction


def _tx(account_id: int, date: datetime, kind: str, amount: float, merchant: str) -> Transaction:
    return Transaction(
        account_id=account_id, date=date, month_label=date.strftime("%Y-%m"), type=kind, merchant=merchant,
        amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
    )


def test_potential_transfers_loads_few_queries_and_full_pairs(client, db_session):
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    livret = Account(name="Livret", type="epargne", currency="EUR", active=True)
    db_session.add_all([courant, livret])
    db_session.flush()
    start = datetime(2024, 1, 1)
    rows = [_tx(courant.id, start + timedelta(hours=i), "Sortie", 1000.0 + i * 7, f"S{i}") for i in range(1200)]
    rows += [_tx(livret.id, start + timedelta(days=400, hours=i), "Entree", 5000.0 + i * 7, f"E{i}") for i in range(1200)]
    pair_day = datetime(2025, 6, 1)
    rows += [_tx(courant.id, pair_day, "Sortie", 123.45, "Virement vers livret"),
             _tx(livret.id, pair_day + timedelta(days=1), "Entree", 123.45, "Virement depuis courant")]
    db_session.add_all(rows)
    db_session.commit()

    statements = []
    engine = db_session.get_bind()

    def listener(conn, cursor, statement, params, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", listener)
    try:
        response = client.get("/transactions/potential-transfers")
    finally:
        event.remove(engine, "before_cursor_execute", listener)

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["sortie"]["merchant"] == "Virement vers livret"
    assert body[0]["entree"]["merchant"] == "Virement depuis courant"
    assert body[0]["day_gap"] == 1 and body[0]["confidence"] == "high"
    assert "tags" in body[0]["sortie"]  # objet complet, comme avant
    assert len(statements) <= 12, f"{len(statements)} requêtes SQL"
