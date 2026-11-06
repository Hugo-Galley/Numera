from typing import cast

from sqlalchemy import Table, bindparam, update
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def account_ledger_chronological(db: Session, account_id: int) -> list[tuple[int, str, float, float | None]]:
    """(id, type, montant, solde courant) du compte par ordre chronologique (date puis id), lus par colonnes :
    aucun objet ORM, donc aucun chargement des relations `selectin`."""
    return [
        (row.id, row.type, row.amount, row.running_balance)
        for row in db.query(Transaction.id, Transaction.type, Transaction.amount, Transaction.running_balance)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    ]


def update_running_balances(db: Session, account_id: int, balances: list[tuple[int, float]]) -> None:
    """Met à jour en masse les seuls soldes modifiés, puis expire les objets du compte déjà présents en session
    (sinon l'identity map garderait l'ancien `running_balance`)."""
    if not balances:
        return
    table = cast(Table, Transaction.__table__)
    db.execute(
        update(table).where(table.c.id == bindparam("tx_id")).values(running_balance=bindparam("balance")),
        [{"tx_id": tx_id, "balance": balance} for tx_id, balance in balances],
    )
    for obj in list(db.identity_map.values()):
        if isinstance(obj, Transaction) and obj.account_id == account_id:
            db.expire(obj, ["running_balance"])
