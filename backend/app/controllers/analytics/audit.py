from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.insight import ActionCenterResponse, DataAuditResponse
from app.services import audit as service

router = APIRouter()


@router.get("/audit", response_model=DataAuditResponse)
def data_audit(db: Session = Depends(get_db)):
    return service.compute_data_audit(db)


@router.get("/audit/{issue_id}")
def data_audit_issue_details(issue_id: str, db: Session = Depends(get_db)):
    return service.compute_data_audit_issue(db, issue_id)


@router.get("/actions", response_model=ActionCenterResponse)
async def get_action_center(db: Session = Depends(get_db)):
    return await service.compute_action_center(db)


class DismissActionRequest(BaseModel):
    id: str


@router.post("/actions/dismiss")
async def dismiss_action(request: DismissActionRequest, db: Session = Depends(get_db)):
    return service.dismiss_action(db, request.id)
