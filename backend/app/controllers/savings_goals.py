from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.savings_goal import SavingsGoal, SavingsGoalCreate, SavingsGoalProgress, SavingsGoalUpdate
from app.services import savings_goals as service

router = APIRouter(prefix="/goals", tags=["savings-goals"])


@router.get("", response_model=List[SavingsGoalProgress])
async def list_goals(db: Session = Depends(get_db)):
    return await service.list_goals(db)


@router.post("", response_model=SavingsGoal)
async def create_goal(goal_in: SavingsGoalCreate, db: Session = Depends(get_db)):
    return service.create_goal(db, goal_in)


@router.patch("/{goal_id}", response_model=SavingsGoal)
async def update_goal(goal_id: int, goal_in: SavingsGoalUpdate, db: Session = Depends(get_db)):
    return service.update_goal(db, goal_id, goal_in)


@router.delete("/{goal_id}")
async def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    return service.delete_goal(db, goal_id)
