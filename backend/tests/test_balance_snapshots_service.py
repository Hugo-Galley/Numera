"""Services relevés de solde, objectifs d'épargne et événements financiers, sans HTTP."""
from datetime import date, datetime, timedelta

import pytest

from app.core.errors import BusinessRuleError, NotFoundError
from app.domain.savings_goals import goal_status
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.schemas.financial_event import FinancialEventCreate
from app.schemas.investment import BalanceSnapshotCreate, SetZeroPointRequest
from app.services.comptes import balance_snapshots as snapshot_service
from app.services.comptes import financial_events as event_service


def _account(db, type_):
    account = Account(name="Compte", type=type_, currency="EUR", active=True)
    db.add(account)
    db.commit()
    return account


def test_snapshot_on_current_account_is_rejected(db_session):
    account = _account(db_session, "courant")
    with pytest.raises(BusinessRuleError, match="Account must be of type investissement or assurance_vie"):
        snapshot_service.create_balance_snapshot(
            db_session, BalanceSnapshotCreate(account_id=account.id, date=datetime(2026, 10, 1), current_value=10.0))


def test_set_zero_point_keeps_a_single_zero_point(db_session):
    account = _account(db_session, "investissement")
    snapshot_service.set_zero_point(db_session, SetZeroPointRequest(account_id=account.id, current_value=100.0))
    snapshot_service.set_zero_point(db_session, SetZeroPointRequest(account_id=account.id))
    zero_points = db_session.query(BalanceSnapshot).filter_by(account_id=account.id, is_zero_point=True).all()
    assert len(zero_points) == 1
    assert zero_points[0].current_value == 100.0  # repris du dernier relevé


def test_snapshot_marks_account_verified(db_session):
    account = _account(db_session, "assurance_vie")
    snapshot_service.create_balance_snapshot(
        db_session, BalanceSnapshotCreate(account_id=account.id, date=datetime(2026, 10, 1), current_value=10.0))
    db_session.refresh(account)
    assert account.last_verified_at is not None


def test_event_on_unknown_account_is_not_found(db_session):
    with pytest.raises(NotFoundError, match="Compte introuvable"):
        event_service.create_financial_event(
            db_session, FinancialEventCreate(date=date(2026, 10, 1), title="Achat", account_id=42))


def test_goal_status_rules():
    today = date(2026, 10, 1)
    assert goal_status(1000.0, 1000.0, None, today)[2] == "completed"
    assert goal_status(850.0, 1000.0, None, today)[2] == "ahead"
    assert goal_status(100.0, 1000.0, today - timedelta(days=1), today)[2] == "behind"
    days, monthly, status = goal_status(400.0, 1000.0, today + timedelta(days=61), today)
    assert (days, status) == (61, "on_track") and round(monthly, 2) == round(600 / (61 / 30.44), 2)
