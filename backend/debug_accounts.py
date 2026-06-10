from app.db.session import SessionLocal
from app.models.account import Account
from app.models.transaction import Transaction
from sqlalchemy import func

db = SessionLocal()
try:
    accounts = db.query(Account).all()
    print(f"{'ID':<5} | {'Name':<20} | {'Type':<15} | {'Active':<8} | {'Tx Count':<10}")
    print("-" * 65)
    for acc in accounts:
        tx_count = db.query(func.count(Transaction.id)).filter(Transaction.account_id == acc.id).scalar()
        print(f"{acc.id:<5} | {acc.name:<20} | {acc.type:<15} | {str(acc.active):<8} | {tx_count:<10}")
finally:
    db.close()
