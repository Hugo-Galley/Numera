from datetime import date

from sqlalchemy.orm import Session

from app.integrations.currency import get_exchange_rates
from app.core.errors import NotFoundError
from app.domain.savings_goals import goal_status, percentage, signed_total_eur
from app.models.savings_goal import SavingsGoal as SavingsGoalModel
from app.repositories.budget import savings_goals as repo
from app.schemas.savings_goal import SavingsGoalCreate, SavingsGoalProgress, SavingsGoalUpdate


def _require(db: Session, goal_id: int) -> SavingsGoalModel:
    goal = repo.get(db, goal_id)
    if not goal:
        raise NotFoundError("Goal not found")
    return goal


def _goal_progress(db: Session, goal: SavingsGoalModel, rates: dict[str, float], today: date) -> SavingsGoalProgress:
    current_amount = signed_total_eur(repo.goal_rows(db, goal), rates)
    days_remaining, monthly_required, status = goal_status(current_amount, goal.target_amount, goal.deadline, today)
    return SavingsGoalProgress(
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
        percentage=round(percentage(current_amount, goal.target_amount), 2),
        monthly_required=round(monthly_required, 2) if monthly_required is not None else None,
        days_remaining=days_remaining,
        status=status
    )


async def list_goals(db: Session) -> list[SavingsGoalProgress]:
    rates = await get_exchange_rates("EUR")
    today = date.today()
    return [_goal_progress(db, goal, rates, today) for goal in repo.list_all(db)]


def create_goal(db: Session, goal_in: SavingsGoalCreate) -> SavingsGoalModel:
    goal = SavingsGoalModel(**goal_in.model_dump())
    repo.add(db, goal)
    db.commit()
    db.refresh(goal)
    return goal


def update_goal(db: Session, goal_id: int, goal_in: SavingsGoalUpdate) -> SavingsGoalModel:
    goal = _require(db, goal_id)
    for field, value in goal_in.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal_id: int) -> dict:
    repo.delete(db, _require(db, goal_id))
    db.commit()
    return {"status": "success"}
