"""`GET /transactions/total` : total net des transactions filtrées (panneau « derrière ce chiffre »)."""
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.transaction_split import TransactionSplit


def _tx(account_id: int, amount: float, category_id: int | None = None, offset: float = 0.0, day: int = 5) -> Transaction:
    return Transaction(
        account_id=account_id, date=datetime(2026, 3, day), type="Sortie", merchant="M", category_id=category_id,
        amount=amount, reimbursement_offset=offset, original_amount=amount, currency="EUR", running_balance=0,
        month_label="Mars",
    )


def _setup(db: Session):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    food = Category(name="Food", type="depense")
    fun = Category(name="Fun", type="depense")
    db.add_all([account, food, fun])
    db.commit()
    return account, food, fun


def test_total_est_net_des_remboursements(client: TestClient, db_session: Session):
    account, food, _ = _setup(db_session)
    db_session.add_all([_tx(account.id, 100, food.id, offset=30), _tx(account.id, 50, food.id)])
    db_session.commit()

    body = client.get("/transactions/total", params={"type": "Sortie"}).json()

    assert body == {"count": 2, "total": 120.0}


def test_total_suit_les_memes_filtres_que_la_liste(client: TestClient, db_session: Session):
    account, food, fun = _setup(db_session)
    db_session.add_all([_tx(account.id, 10, food.id), _tx(account.id, 25, fun.id)])
    db_session.commit()

    body = client.get("/transactions/total", params={"category_id": fun.id}).json()

    assert body == {"count": 1, "total": 25.0}


def test_total_ne_compte_que_la_part_de_la_categorie_filtree(client: TestClient, db_session: Session):
    account, food, fun = _setup(db_session)
    tx = _tx(account.id, 100, food.id, offset=20)
    db_session.add(tx)
    db_session.flush()
    db_session.add_all([
        TransactionSplit(transaction_id=tx.id, category_id=food.id, amount=60),
        TransactionSplit(transaction_id=tx.id, category_id=fun.id, amount=40),
    ])
    db_session.commit()

    # net 80 réparti 60/40 : la part « fun » vaut 80 * 40 / 100
    assert client.get("/transactions/total", params={"category_id": fun.id}).json() == {"count": 1, "total": 32.0}
    # sans filtre de catégorie, la dépense compte en entier (net)
    assert client.get("/transactions/total").json() == {"count": 1, "total": 80.0}


def test_total_vide(client: TestClient, db_session: Session):
    assert client.get("/transactions/total").json() == {"count": 0, "total": 0.0}


def test_total_sans_doublon_avec_filtre_tags(client: TestClient, db_session: Session):
    from app.models.tag import Tag

    account, food, _ = _setup(db_session)
    tx = _tx(account.id, 40, food.id)
    t1, t2 = Tag(name="a"), Tag(name="b")
    tx.tags = [t1, t2]
    db_session.add(tx)
    db_session.commit()

    body = client.get("/transactions/total", params={"tag_ids": [t1.id, t2.id]}).json()

    assert body == {"count": 1, "total": 40.0}
