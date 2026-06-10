from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List
from datetime import date, datetime

from app.db.session import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.savings_goal import SavingsGoal as SavingsGoalModel
from app.models.transaction import Transaction
from app.schemas.savings_goal import SavingsGoal, SavingsGoalCreate, SavingsGoalUpdate, SavingsGoalProgress
from app.core.currency import get_exchange_rates

router = APIRouter(prefix="/goals", tags=["savings-goals"])


@router.get("", response_model=List[SavingsGoalProgress])
async def list_goals(db: Session = Depends(get_db)):
    goals = db.query(SavingsGoalModel).all()
    rates = await get_exchange_rates("EUR")
    today = date.today()
    
    results = []
    for goal in goals:
        # Build dynamic filter
        filters = []
        if goal.keyword:
            filters.append(or_(
                Transaction.note.ilike(f"%{goal.keyword}%"),
                Transaction.merchant.ilike(f"%{goal.keyword}%"),
                Category.name.ilike(f"%{goal.keyword}%")
            ))
        
        query = db.query(Transaction, Account.currency).join(Account).outerjoin(Category)
        
        if goal.account_id:
            query = query.filter(Transaction.account_id == goal.account_id)
        
        if goal.category_id:
            query = query.filter(Transaction.category_id == goal.category_id)
            
        if filters:
            query = query.filter(or_(*filters))
        
        # If no filters at all (no keyword, no account, no category), 
        # we might want to return 0 or everything. Let's say 0 for safety.
        if not goal.keyword and not goal.account_id and not goal.category_id:
            tx_rows = []
        else:
            tx_rows = query.all()
        
        current_amount = 0.0
        for tx, curr in tx_rows:
            val_eur = tx.amount / rates.get(curr, 1.0)
            if tx.type in ["Entree", "Interets", "Solde Initial"]:
                current_amount += val_eur
            else:
                current_amount -= val_eur
        
        percentage = (current_amount / goal.target_amount * 100.0) if goal.target_amount > 0 else 0.0
        
        # Enriched fields
        days_remaining = None
        monthly_required = None
        status = "on_track"
        
        if goal.deadline:
            days_remaining = (goal.deadline - today).days
            if days_remaining > 0:
                months_rem = days_remaining / 30.44
                remaining_amount = max(0, goal.target_amount - current_amount)
                monthly_required = remaining_amount / months_rem if months_rem > 0 else remaining_amount
            elif days_remaining <= 0 and current_amount < goal.target_amount:
                status = "behind"
        
        if current_amount >= goal.target_amount:
            status = "completed"
        elif percentage > 80: # Simple logic for now
            status = "ahead"
            
        results.append(SavingsGoalProgress(
            id=goal.id,
            name=goal.name,
            target_amount=goal.target_amount,
            keyword=goal.keyword,
            icon=goal.icon,
            color=goal.color,
            deadline=goal.deadline,
            account_id=goal.account_id,
            category_id=goal.category_id,
            current_amount=round(current_amount, 2),
            percentage=round(percentage, 2),
            monthly_required=round(monthly_required, 2) if monthly_required is not None else None,
            days_remaining=days_remaining,
            status=status
        ))
    
    return results


@router.post("", response_model=SavingsGoal)
async def create_goal(goal_in: SavingsGoalCreate, db: Session = Depends(get_db)):
    goal = SavingsGoalModel(**goal_in.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.patch("/{goal_id}", response_model=SavingsGoal)
async def update_goal(goal_id: int, goal_in: SavingsGoalUpdate, db: Session = Depends(get_db)):
    goal = db.query(SavingsGoalModel).filter(SavingsGoalModel.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    update_data = goal_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)
    
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/{goal_id}")
async def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(SavingsGoalModel).filter(SavingsGoalModel.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()
    return {"status": "success"}
