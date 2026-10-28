from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.investment import BalanceSnapshotCreate, BalanceSnapshotRead, BalanceSnapshotUpdate, SetZeroPointRequest
from app.services import balance_snapshots as service

router = APIRouter(prefix="/balance-snapshots", tags=["balance-snapshots"])


@router.get("", response_model=list[BalanceSnapshotRead])
def list_balance_snapshots(account_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    return service.list_balance_snapshots(db, account_id)


@router.post("", response_model=BalanceSnapshotRead, status_code=201)
def create_balance_snapshot(payload: BalanceSnapshotCreate, db: Session = Depends(get_db)):
    return service.create_balance_snapshot(db, payload)


@router.delete("/{snapshot_id}", status_code=204)
def delete_balance_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    service.delete_balance_snapshot(db, snapshot_id)


@router.patch("/{snapshot_id}", response_model=BalanceSnapshotRead)
def update_balance_snapshot(snapshot_id: int, payload: BalanceSnapshotUpdate, db: Session = Depends(get_db)):
    return service.update_balance_snapshot(db, snapshot_id, payload)


@router.post("/set-zero-point", response_model=BalanceSnapshotRead, status_code=201)
def set_zero_point(payload: SetZeroPointRequest, db: Session = Depends(get_db)):
    return service.set_zero_point(db, payload)
