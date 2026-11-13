from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.sync_bridge import run_async
from app.db.session import get_db
from app.schemas.budget_tools import DividendLinkResult
from app.schemas.investment import InvestmentTransactionCreate, InvestmentTransactionRead, InvestmentTransactionUpdate
from app.services.investissement import investment_transactions as service

if TYPE_CHECKING:
    from app.models.investment_transaction import InvestmentTransaction

router = APIRouter(prefix="/investment-transactions", tags=["investment-transactions"])


@router.get("", response_model=list[InvestmentTransactionRead])
def list_investment_transactions(
    account_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int | None = Query(default=None, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> "list[InvestmentTransaction]":
    return service.list_transactions(db, account_id, skip, limit)


@router.post("/link-dividends", response_model=DividendLinkResult)
def link_dividends(
    account_id: int = Query(...),
    dry_run: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Rattache les dividendes sans titre d'un compte à une de ses positions, d'après leur libellé
    (« Dividende Apple » → AAPL). `dry_run=true` (défaut) se contente de proposer ; les libellés
    ambigus ou inconnus restent non rattachés.
    """
    return service.link_dividends(db, account_id, dry_run)


@router.post("", response_model=InvestmentTransactionRead, status_code=201)
def create_investment_transaction(payload: InvestmentTransactionCreate, db: Session = Depends(get_db)) -> "InvestmentTransaction":
    return run_async(service.create_transaction(db, payload))


@router.delete("/{transaction_id}", status_code=204)
def delete_investment_transaction(transaction_id: int, db: Session = Depends(get_db)) -> None:
    run_async(service.delete_transaction(db, transaction_id))


@router.patch("/{transaction_id}", response_model=InvestmentTransactionRead)
def update_investment_transaction(transaction_id: int, payload: InvestmentTransactionUpdate, db: Session = Depends(get_db)) -> "InvestmentTransaction":
    return run_async(service.update_transaction(db, transaction_id, payload))
