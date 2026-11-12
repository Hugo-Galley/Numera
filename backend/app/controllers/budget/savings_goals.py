from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.sync_bridge import run_async
from app.db.session import get_db
from app.schemas.common import StatusResponse
from app.schemas.savings_goal import SavingsGoal, SavingsGoalCreate, SavingsGoalProgress, SavingsGoalUpdate
from app.services.budget import savings_goals as service

if TYPE_CHECKING:
    from app.models.savings_goal import SavingsGoal as SavingsGoalModel

router = APIRouter(prefix="/goals", tags=["savings-goals"])


@router.get("", response_model=list[SavingsGoalProgress])
def list_goals(db: Session = Depends(get_db)) -> list[SavingsGoalProgress]:
    return run_async(service.list_goals(db))


@router.post("", response_model=SavingsGoal)
def create_goal(goal_in: SavingsGoalCreate, db: Session = Depends(get_db)) -> "SavingsGoalModel":
    return service.create_goal(db, goal_in)


@router.patch("/{goal_id}", response_model=SavingsGoal)
def update_goal(goal_id: int, goal_in: SavingsGoalUpdate, db: Session = Depends(get_db)) -> "SavingsGoalModel":
    return service.update_goal(db, goal_id, goal_in)


@router.delete("/{goal_id}", response_model=StatusResponse)
def delete_goal(goal_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    return service.delete_goal(db, goal_id)
