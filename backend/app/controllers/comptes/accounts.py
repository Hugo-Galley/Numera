from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.sync_bridge import run_async
from app.db.session import get_db
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate, ReconcileRequest, ReconcileResult
from app.services.comptes import accounts as service

if TYPE_CHECKING:
    from app.models.account import Account

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountRead])
def list_accounts(db: Session = Depends(get_db)) -> "list[Account]":
    return run_async(service.list_accounts(db))


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, db: Session = Depends(get_db)) -> "Account":
    return run_async(service.get_account(db, account_id))


@router.post("", response_model=AccountRead, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)) -> "Account":
    return service.create_account(db, payload)


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)) -> "Account":
    return run_async(service.update_account(db, account_id, payload))


@router.post("/{account_id}/verify", response_model=AccountRead)
def verify_account(account_id: int, db: Session = Depends(get_db)) -> "Account":
    return run_async(service.verify_account(db, account_id))


@router.post("/{account_id}/reconcile", response_model=ReconcileResult)
def reconcile_account(account_id: int, payload: ReconcileRequest, db: Session = Depends(get_db)) -> ReconcileResult:
    """Compare le solde affiché par la banque à celui de Numera et propose les causes d'un écart."""
    return service.reconcile_account(db, account_id, payload)


@router.delete("/{account_id}", status_code=204)
def archive_account(account_id: int, db: Session = Depends(get_db)) -> None:
    service.archive_account(db, account_id)
