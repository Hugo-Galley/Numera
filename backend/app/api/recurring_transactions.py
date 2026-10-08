from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction
from app.schemas.recurring_transaction import RecurringTransactionCreate, RecurringTransactionRead, RecurringTransactionUpdate
from app.core.recurring import generate_recurring_transactions

router = APIRouter(prefix="/recurring-transactions", tags=["recurring-transactions"])


def _validate_transfer_target(db: Session, account_id: int, type_: str, ticker: str | None, dest_id: int | None) -> None:
    """Une récurrence « virement » est une Sortie d'un compte non titres vers un autre compte."""
    if dest_id is None:
        return
    source = db.query(Account).filter(Account.id == account_id).first()
    dest = db.query(Account).filter(Account.id == dest_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination account not found")
    if dest_id == account_id:
        raise HTTPException(status_code=422, detail="Source and destination accounts must differ")
    if type_ != "Sortie":
        raise HTTPException(status_code=422, detail="A transfer recurrence must be a Sortie")
    if ticker or (source and source.type == "investissement"):
        raise HTTPException(status_code=422, detail="A transfer recurrence cannot come from a securities account")

@router.post("/trigger", response_model=int)
async def trigger_generation(db: Session = Depends(get_db)) -> int:
    """Manually trigger the generation of recurring transactions."""
    return await generate_recurring_transactions(db)

@router.get("/", response_model=list[RecurringTransactionRead])
async def read_recurring_transactions(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    trigger: bool = Query(default=False)
) -> Any:
    if trigger:
        await generate_recurring_transactions(db)
    return db.query(RecurringTransaction).offset(skip).limit(limit).all()

@router.post("/", response_model=RecurringTransactionRead)
async def create_recurring_transaction(
    *,
    db: Session = Depends(get_db),
    recurring_tx_in: RecurringTransactionCreate,
) -> Any:
    data = recurring_tx_in.model_dump()
    # Convert list[int] to CSV string for DB storage
    if data.get("excluded_months") is not None:
        data["excluded_months"] = ",".join(str(m) for m in data["excluded_months"])
    _validate_transfer_target(db, data["account_id"], data["type"], data.get("ticker"), data.get("transfer_to_account_id"))
    recurring_tx = RecurringTransaction(**data)
    db.add(recurring_tx)
    db.commit()
    db.refresh(recurring_tx)

    if recurring_tx.auto_generate and recurring_tx.is_active:
        try:
            await generate_recurring_transactions(db)
            db.refresh(recurring_tx)
        except Exception:
            pass

    return recurring_tx

@router.patch("/{recurring_tx_id}", response_model=RecurringTransactionRead)
async def update_recurring_transaction(
    *,
    db: Session = Depends(get_db),
    recurring_tx_id: int,
    recurring_tx_in: RecurringTransactionUpdate,
) -> Any:
    recurring_tx = db.query(RecurringTransaction).filter(RecurringTransaction.id == recurring_tx_id).first()
    if not recurring_tx:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    
    update_data = recurring_tx_in.model_dump(exclude_unset=True)
    # Convert list[int] to CSV string for DB storage
    if "excluded_months" in update_data:
        if update_data["excluded_months"] is not None:
            update_data["excluded_months"] = ",".join(str(m) for m in update_data["excluded_months"])
        else:
            update_data["excluded_months"] = None
    _validate_transfer_target(
        db,
        update_data.get("account_id", recurring_tx.account_id),
        update_data.get("type", recurring_tx.type),
        update_data.get("ticker", recurring_tx.ticker),
        update_data.get("transfer_to_account_id", recurring_tx.transfer_to_account_id),
    )
    for field, value in update_data.items():
        setattr(recurring_tx, field, value)
    
    db.add(recurring_tx)
    db.commit()
    db.refresh(recurring_tx)

    if recurring_tx.auto_generate and recurring_tx.is_active:
        try:
            await generate_recurring_transactions(db)
            db.refresh(recurring_tx)
        except Exception:
            pass

    return recurring_tx

@router.delete("/{recurring_tx_id}")
def delete_recurring_transaction(
    *,
    db: Session = Depends(get_db),
    recurring_tx_id: int,
) -> Any:
    recurring_tx = db.query(RecurringTransaction).filter(RecurringTransaction.id == recurring_tx_id).first()
    if not recurring_tx:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    
    # Unlink existing transactions from this recurring rule
    from app.models.transaction import Transaction
    from app.models.investment_transaction import InvestmentTransaction
    
    db.query(Transaction).filter(Transaction.recurring_transaction_id == recurring_tx_id).update(
        {Transaction.recurring_transaction_id: None}, synchronize_session=False
    )
    db.query(InvestmentTransaction).filter(InvestmentTransaction.recurring_transaction_id == recurring_tx_id).update(
        {InvestmentTransaction.recurring_transaction_id: None}, synchronize_session=False
    )

    from app.models.salary_config import SalaryConfig
    db.query(SalaryConfig).filter(SalaryConfig.salary_recurring_id == recurring_tx_id).update(
        {SalaryConfig.salary_recurring_id: None}, synchronize_session=False
    )
    db.query(SalaryConfig).filter(SalaryConfig.ticket_recurring_id == recurring_tx_id).update(
        {SalaryConfig.ticket_recurring_id: None}, synchronize_session=False
    )

    db.delete(recurring_tx)
    db.commit()
    return {"message": "Recurring transaction deleted"}
