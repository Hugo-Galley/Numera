from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.core.sync_bridge import run_async
from app.schemas.analytics_reports import AuditIssueDetails
from app.schemas.common import StatusResponse
from app.schemas.insight import ActionCenterResponse, DataAuditResponse
from app.services import audit as service

router = APIRouter()


@router.get("/audit", response_model=DataAuditResponse)
def data_audit(db: Session = Depends(get_db)) -> DataAuditResponse:
    return service.compute_data_audit(db)


@router.get("/audit/{issue_id}", response_model=AuditIssueDetails, response_model_exclude_unset=True)
def data_audit_issue_details(issue_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    return service.compute_data_audit_issue(db, issue_id)


@router.get("/actions", response_model=ActionCenterResponse)
def get_action_center(db: Session = Depends(get_db)) -> ActionCenterResponse:
    return run_async(service.compute_action_center(db))


class DismissActionRequest(BaseModel):
    id: str


@router.post("/actions/dismiss", response_model=StatusResponse)
def dismiss_action(request: DismissActionRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    return service.dismiss_action(db, request.id)
