import pytest

from app.core.errors import BusinessRuleError, NotFoundError
from app.models.account import Account
from app.schemas.transfer_rule import TransferRuleCreate
from app.services.budget import transfer_rules as service


def _account(db, name):
    account = Account(name=name, type="courant", currency="EUR", active=True)
    db.add(account)
    db.commit()
    return account


def test_rule_with_same_source_and_destination_is_rejected(db_session):
    account = _account(db_session, "Courant")
    with pytest.raises(BusinessRuleError, match="Source and destination accounts must differ"):
        service.create_rule(db_session, TransferRuleCreate(source_account_id=account.id, dest_account_id=account.id))


def test_rule_on_unknown_account_is_not_found(db_session):
    account = _account(db_session, "Courant")
    with pytest.raises(NotFoundError, match="Account not found"):
        service.create_rule(db_session, TransferRuleCreate(source_account_id=account.id, dest_account_id=999))
