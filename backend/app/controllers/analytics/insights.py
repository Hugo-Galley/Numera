from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.insight import IntelligentInsights
from app.services.analytics import insights as service

router = APIRouter()


@router.get("/insights", response_model=IntelligentInsights)
async def get_intelligent_insights(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return await service.compute_insights(db, month, year, account_id)


class DismissInsightRequest(BaseModel):
    title: str


@router.post("/insights/dismiss")
async def dismiss_insight(request: DismissInsightRequest, db: Session = Depends(get_db)):
    return service.dismiss_insight(db, request.title)
