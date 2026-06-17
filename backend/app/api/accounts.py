from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.db.session import get_db
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.transaction import Transaction
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _get_balance_for_account(db: Session, account_id: int) -> float:
    latest_snap = db.query(BalanceSnapshot).filter(
        BalanceSnapshot.account_id == account_id
    ).order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()).first()
    
    if latest_snap:
        return float(latest_snap.current_value)
        
    latest_tx = db.query(Transaction).filter(
        Transaction.account_id == account_id
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
    
    if latest_tx:
        return float(latest_tx.running_balance)
        
    return 0.0


@router.get("", response_model=list[AccountRead])
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).order_by(Account.id.asc()).all()
    for acc in accounts:
        acc.balance = _get_balance_for_account(db, acc.id)
    return accounts


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise api_error(404, "account_not_found", "Account not found", {"account_id": account_id})
    account.balance = _get_balance_for_account(db, account.id)
    return account


@router.post("", response_model=AccountRead, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    account = Account(
        name=payload.name,
        type=payload.type,
        currency=payload.currency,
        color=payload.color,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    account.balance = 0.0
    return account


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise api_error(404, "account_not_found", "Account not found", {"account_id": account_id})

    data = payload.model_dump(exclude_unset=True)
    
    if data.get("is_main") is True:
        db.query(Account).filter(Account.id != account_id).update({"is_main": False})

    for key, value in data.items():
        setattr(account, key, value)


    db.commit()
    db.refresh(account)
    account.balance = _get_balance_for_account(db, account.id)
    return account


@router.post("/{account_id}/verify", response_model=AccountRead)
def verify_account(account_id: int, db: Session = Depends(get_db)):
    from app.core.time import utcnow_naive
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise api_error(404, "account_not_found", "Account not found", {"account_id": account_id})
    account.last_verified_at = utcnow_naive()
    db.commit()
    db.refresh(account)
    account.balance = _get_balance_for_account(db, account.id)
    return account


@router.delete("/{account_id}", status_code=204)
def archive_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise api_error(404, "account_not_found", "Account not found", {"account_id": account_id})
    account.active = False
    db.commit()
