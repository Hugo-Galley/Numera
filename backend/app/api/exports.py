import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.investment_transaction import InvestmentTransaction

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/transactions.csv")
def export_transactions_csv(
    account_ids: str | None = Query(default=None, description="Comma-separated list of account IDs"),
    db: Session = Depends(get_db),
):
    ids = []
    if account_ids:
        try:
            ids = [int(i.strip()) for i in account_ids.split(",") if i.strip()]
        except ValueError:
            pass

    # Fetch regular transactions
    query_tx = db.query(Transaction)
    if ids:
        query_tx = query_tx.filter(Transaction.account_id.in_(ids))
    transactions = query_tx.all()

    # Fetch investment transactions
    query_inv = db.query(InvestmentTransaction)
    if ids:
        query_inv = query_inv.filter(InvestmentTransaction.account_id.in_(ids))
    inv_transactions = query_inv.all()

    # Combine and sort
    # We create a unified format for sorting and writing
    combined = []
    
    category_ids = {tx.category_id for tx in transactions if tx.category_id is not None}
    categories = {}
    if category_ids:
        categories = {
            category.id: category.name
            for category in db.query(Category).filter(Category.id.in_(list(category_ids))).all()
        }

    unique_account_ids = {tx.account_id for tx in transactions} | {tx.account_id for tx in inv_transactions}
    accounts = {}
    if unique_account_ids:
        accounts = {
            account.id: account.name
            for account in db.query(Account).filter(Account.id.in_(list(unique_account_ids))).all()
        }

    for tx in transactions:
        combined.append({
            "account_id": tx.account_id,
            "account_name": accounts.get(tx.account_id, f"Compte {tx.account_id}"),
            "date": tx.date,
            "month_label": tx.month_label,
            "type": "Type" if tx.type == "Solde Initial" else tx.type,
            "merchant": tx.merchant,
            "category": categories.get(tx.category_id, "") if tx.category_id else "",
            "amount": tx.amount,
            "balance": tx.running_balance
        })

    for tx in inv_transactions:
        # Investment transactions don't have merchants or categories in the same way
        # But we can map them to the same columns
        combined.append({
            "account_id": tx.account_id,
            "account_name": accounts.get(tx.account_id, f"Compte {tx.account_id}"),
            "date": tx.date,
            "month_label": tx.date.strftime("%B"), # Simple fallback, could be improved if needed
            "type": tx.type,
            "merchant": "Investissement",
            "category": "Investissement",
            "amount": tx.amount,
            "balance": 0.0 # Investment transactions don't store running balance in this table
        })

    # Sort by account name then date
    combined.sort(key=lambda x: (x["account_name"], x["date"]))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Compte", "Date", "Mois", "Type", "Commercant", "Categorie", "Montant", "Solde Compte"])

    for item in combined:
        date_str = item["date"].strftime("%d/%m/%Y %H:%M") if isinstance(item["date"], datetime) else ""
        writer.writerow(
            [
                item["account_name"],
                date_str,
                item["month_label"],
                item["type"],
                item["merchant"],
                item["category"],
                f"{item['amount']:.2f}",
                f"{item['balance']:.2f}",
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions_export.csv"},
    )
