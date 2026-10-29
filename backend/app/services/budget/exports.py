"""Export CSV des transactions et opérations d'investissement (format Numbers)."""
from sqlalchemy.orm import Session

from app.domain.exports import to_csv
from app.repositories.budget import exports as repo


def _parse_ids(account_ids: str | None) -> list[int]:
    if not account_ids:
        return []
    try:
        return [int(i.strip()) for i in account_ids.split(",") if i.strip()]
    except ValueError:
        return []


def export_transactions_csv(db: Session, account_ids: str | None) -> str:
    ids = _parse_ids(account_ids)
    transactions = repo.transactions(db, ids)
    inv_transactions = repo.investment_transactions(db, ids)
    categories = repo.category_names(db, {tx.category_id for tx in transactions if tx.category_id is not None})
    accounts = repo.account_names(db, {tx.account_id for tx in transactions} | {tx.account_id for tx in inv_transactions})

    def account_name(account_id: int) -> str:
        return accounts.get(account_id, f"Compte {account_id}")

    rows = [{
        "account_name": account_name(tx.account_id),
        "date": tx.date,
        "month_label": tx.month_label,
        "type": "Type" if tx.type == "Solde Initial" else tx.type,
        "merchant": tx.merchant,
        "category": categories.get(tx.category_id, "") if tx.category_id else "",
        "amount": tx.amount,
        "balance": tx.running_balance,
    } for tx in transactions]
    # Les opérations d'investissement n'ont ni marchand, ni catégorie, ni solde courant
    rows += [{
        "account_name": account_name(tx.account_id),
        "date": tx.date,
        "month_label": tx.date.strftime("%B"),
        "type": tx.type,
        "merchant": "Investissement",
        "category": "Investissement",
        "amount": tx.amount,
        "balance": 0.0,
    } for tx in inv_transactions]
    return to_csv(rows)
