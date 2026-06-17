import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.investment_transaction import InvestmentTransaction
from app.models.balance_snapshot import BalanceSnapshot
from sqlalchemy import func

def main():
    db = SessionLocal()
    accounts = db.query(Account).all()
    for acc in accounts:
        latest_date = acc.created_at

        # Check latest transaction
        latest_tx = db.query(func.max(Transaction.date)).filter(Transaction.account_id == acc.id).scalar()
        if latest_tx and latest_tx > latest_date:
            latest_date = latest_tx
        
        # Check latest investment transaction
        latest_inv_tx = db.query(func.max(InvestmentTransaction.date)).filter(InvestmentTransaction.account_id == acc.id).scalar()
        if latest_inv_tx and latest_inv_tx > latest_date:
            latest_date = latest_inv_tx
            
        # Check latest balance snapshot
        latest_snap = db.query(func.max(BalanceSnapshot.date)).filter(BalanceSnapshot.account_id == acc.id).scalar()
        if latest_snap and latest_snap > latest_date:
            latest_date = latest_snap
            
        acc.last_verified_at = latest_date
        print(f"Set last_verified_at for {acc.name} to {latest_date}")
        
    db.commit()
    db.close()

if __name__ == "__main__":
    main()
