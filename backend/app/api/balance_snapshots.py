from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.time import utcnow_naive
from app.db.session import get_db
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.schemas.investment import BalanceSnapshotCreate, BalanceSnapshotRead, BalanceSnapshotUpdate, SetZeroPointRequest

router = APIRouter(prefix="/balance-snapshots", tags=["balance-snapshots"])


@router.get("", response_model=list[BalanceSnapshotRead])
def list_balance_snapshots(
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(BalanceSnapshot)
    if account_id is not None:
        query = query.filter(BalanceSnapshot.account_id == account_id)
    return query.order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc()).all()


@router.post("", response_model=BalanceSnapshotRead, status_code=201)
def create_balance_snapshot(payload: BalanceSnapshotCreate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == payload.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.type != "investissement":
        raise HTTPException(status_code=422, detail="Account must be of type investissement")

    if payload.is_zero_point:
        existing_zero_points = db.query(BalanceSnapshot).filter(
            BalanceSnapshot.account_id == payload.account_id,
            BalanceSnapshot.is_zero_point.is_(True),
        )
        for snapshot in existing_zero_points:
            snapshot.is_zero_point = False

    snapshot = BalanceSnapshot(
        account_id=payload.account_id,
        date=payload.date,
        current_value=payload.current_value,
        note=payload.note,
        is_zero_point=payload.is_zero_point,
    )
    db.add(snapshot)
    
    from app.core.time import utcnow_naive
    account.last_verified_at = utcnow_naive()
    
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.delete("/{snapshot_id}", status_code=204)
def delete_balance_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.query(BalanceSnapshot).filter(BalanceSnapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Balance snapshot not found")
    db.delete(snapshot)
    db.commit()


@router.patch("/{snapshot_id}", response_model=BalanceSnapshotRead)
def update_balance_snapshot(snapshot_id: int, payload: BalanceSnapshotUpdate, db: Session = Depends(get_db)):
    snapshot = db.query(BalanceSnapshot).filter(BalanceSnapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Balance snapshot not found")

    data = payload.model_dump(exclude_unset=True)
    if data.get("is_zero_point") is True:
        existing_zero_points = db.query(BalanceSnapshot).filter(
            BalanceSnapshot.account_id == snapshot.account_id,
            BalanceSnapshot.is_zero_point.is_(True),
            BalanceSnapshot.id != snapshot.id,
        )
        for item in existing_zero_points:
            item.is_zero_point = False

    for key, value in data.items():
        setattr(snapshot, key, value)

    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.post("/set-zero-point", response_model=BalanceSnapshotRead, status_code=201)
def set_zero_point(payload: SetZeroPointRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == payload.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.type != "investissement":
        raise HTTPException(status_code=422, detail="Account must be of type investissement")

    existing_zero_points = db.query(BalanceSnapshot).filter(
        BalanceSnapshot.account_id == payload.account_id,
        BalanceSnapshot.is_zero_point.is_(True),
    )
    for item in existing_zero_points:
        item.is_zero_point = False

    latest_snapshot = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == payload.account_id)
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )

    snapshot = BalanceSnapshot(
        account_id=payload.account_id,
        date=payload.date or utcnow_naive(),
        current_value=payload.current_value if payload.current_value is not None else (latest_snapshot.current_value if latest_snapshot else 0.0),
        note=payload.note or "Nouveau point zero",
        is_zero_point=True,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
