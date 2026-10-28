from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate, ReconcileRequest, ReconcileResult
from app.services import accounts as service

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountRead])
def list_accounts(db: Session = Depends(get_db)):
    return service.list_accounts(db)


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, db: Session = Depends(get_db)):
    return service.get_account(db, account_id)


@router.post("", response_model=AccountRead, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    return service.create_account(db, payload)


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    return service.update_account(db, account_id, payload)


@router.post("/{account_id}/verify", response_model=AccountRead)
def verify_account(account_id: int, db: Session = Depends(get_db)):
    return service.verify_account(db, account_id)


@router.post("/{account_id}/reconcile", response_model=ReconcileResult)
def reconcile_account(account_id: int, payload: ReconcileRequest, db: Session = Depends(get_db)):
    """Compare le solde affiché par la banque à celui de Numera et propose les causes d'un écart."""
    return service.reconcile_account(db, account_id, payload)


@router.delete("/{account_id}", status_code=204)
def archive_account(account_id: int, db: Session = Depends(get_db)):
    service.archive_account(db, account_id)
