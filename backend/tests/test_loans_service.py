"""Services crédits et provisions, sans HTTP."""
from datetime import date

import pytest

from app.core.errors import NotFoundError
from app.domain.loans import add_months
from app.models.account import Account
from app.models.loan import Loan
from app.schemas.loan import LoanCreate
from app.schemas.provision import ProvisionCreate
from app.services.comptes import accounts as account_service
from app.services.comptes import loans as loan_service
from app.services import provisions as provision_service


def _payload(**overrides):
    data = dict(name="Prêt auto", principal=12000.0, annual_rate_pct=3.0, duration_months=48,
                start_date=add_months(date.today().replace(day=1), -6))
    data.update(overrides)
    return LoanCreate(**data)


def test_create_loan_creates_credit_account(db_session):
    summary = loan_service.create_loan(db_session, _payload())
    account = db_session.get(Account, summary.account_id)
    assert account.type == "credit"
    assert account_service.account_balance(db_session, account.id) == pytest.approx(-summary.remaining_principal)
    assert 0 < summary.remaining_principal < 12000.0


def test_delete_loan_removes_credit_account(db_session):
    summary = loan_service.create_loan(db_session, _payload())
    loan_service.delete_loan(db_session, summary.id)
    db_session.expire_all()
    assert db_session.get(Account, summary.account_id) is None
    assert db_session.get(Loan, summary.id) is None


def test_loan_remaining_is_none_without_loan(db_session):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    assert loan_service.loan_remaining(db_session, account.id, date.today()) is None


def test_unknown_loan_is_not_found(db_session):
    with pytest.raises(NotFoundError, match="Crédit introuvable"):
        loan_service.get_loan(db_session, 1)


def test_provision_with_unknown_category_is_not_found(db_session):
    import asyncio

    with pytest.raises(NotFoundError, match="Catégorie introuvable"):
        asyncio.run(provision_service.create_provision(
            db_session, ProvisionCreate(name="Taxe foncière", amount=900.0, interval_months=12,
                                        due_date=date(2027, 10, 15), category_id=99)))
