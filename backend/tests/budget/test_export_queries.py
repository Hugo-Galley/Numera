"""L'export CSV ne charge pas d'objets ORM complets : nombre de requêtes constant, quel que soit le volume."""
from datetime import datetime, timedelta

from app.models.account import Account
from app.models.transaction import Transaction


def test_export_runs_in_few_queries_and_keeps_every_row(client, db_session, measure_queries):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.flush()
    start = datetime(2024, 1, 1)
    db_session.add_all([
        Transaction(
            account_id=account.id, date=start + timedelta(hours=i), month_label="2024-01", type="Sortie",
            merchant=f"M{i}", amount=1.0 + i, original_amount=1.0 + i, currency="EUR", running_balance=0.0,
        )
        for i in range(1200)
    ])
    db_session.commit()

    response, queries = measure_queries(lambda: client.get("/export/transactions.csv"))

    lines = response.text.strip().splitlines()
    assert response.status_code == 200
    assert len(lines) == 1201  # en-tête + 1200 lignes
    assert "Courant" in lines[1] and "M0" in lines[1]
    assert queries <= 8, f"{queries} requêtes SQL"
