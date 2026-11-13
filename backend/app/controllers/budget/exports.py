from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.budget import exports as service

router = APIRouter(prefix="/export", tags=["export"])


@router.get(
    "/transactions.csv",
    responses={200: {"content": {"text/csv": {"schema": {"type": "string"}}}, "description": "Export CSV des transactions"}},
)
def export_transactions_csv(
    account_ids: str | None = Query(default=None, description="Comma-separated list of account IDs"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        iter([service.export_transactions_csv(db, account_ids)]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions_export.csv"},
    )
