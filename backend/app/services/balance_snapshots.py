from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.time import utcnow_naive
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.repositories import balance_snapshots as repo
from app.schemas.investment import BalanceSnapshotCreate, BalanceSnapshotUpdate, SetZeroPointRequest

VALUED_ACCOUNT_TYPES = ("investissement", "assurance_vie")


def _require_valued_account(db: Session, account_id: int) -> Account:
    account = repo.get_account(db, account_id)
    if not account:
        raise NotFoundError("Account not found")
    if account.type not in VALUED_ACCOUNT_TYPES:
        raise BusinessRuleError("Account must be of type investissement or assurance_vie")
    return account


def _require(db: Session, snapshot_id: int) -> BalanceSnapshot:
    snapshot = repo.get(db, snapshot_id)
    if not snapshot:
        raise NotFoundError("Balance snapshot not found")
    return snapshot


def list_balance_snapshots(db: Session, account_id: int | None) -> list[BalanceSnapshot]:
    return repo.list_for(db, account_id)


def create_balance_snapshot(db: Session, payload: BalanceSnapshotCreate) -> BalanceSnapshot:
    account = _require_valued_account(db, payload.account_id)
    if payload.is_zero_point:
        repo.clear_zero_points(db, payload.account_id)
    snapshot = BalanceSnapshot(
        account_id=payload.account_id,
        date=payload.date,
        current_value=payload.current_value,
        note=payload.note,
        is_zero_point=payload.is_zero_point,
    )
    repo.add(db, snapshot)
    account.last_verified_at = utcnow_naive()
    db.commit()
    db.refresh(snapshot)
    return snapshot


def delete_balance_snapshot(db: Session, snapshot_id: int) -> None:
    repo.delete(db, _require(db, snapshot_id))
    db.commit()


def update_balance_snapshot(db: Session, snapshot_id: int, payload: BalanceSnapshotUpdate) -> BalanceSnapshot:
    snapshot = _require(db, snapshot_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_zero_point") is True:
        repo.clear_zero_points(db, snapshot.account_id, except_id=snapshot.id)
    for key, value in data.items():
        setattr(snapshot, key, value)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def set_zero_point(db: Session, payload: SetZeroPointRequest) -> BalanceSnapshot:
    _require_valued_account(db, payload.account_id)
    repo.clear_zero_points(db, payload.account_id)
    latest_snapshot = repo.latest(db, payload.account_id)
    snapshot = BalanceSnapshot(
        account_id=payload.account_id,
        date=payload.date or utcnow_naive(),
        current_value=payload.current_value if payload.current_value is not None else (latest_snapshot.current_value if latest_snapshot else 0.0),
        note=payload.note or "Nouveau point zero",
        is_zero_point=True,
    )
    repo.add(db, snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
