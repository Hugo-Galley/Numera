"""Génération mensuelle des transactions d'aides (prime d'activité, APL…) et remplacement par le vrai versement."""
from datetime import date, datetime

import pytest

from app.core.errors import BusinessRuleError
from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.benefit import Benefit
from app.models.transaction import Transaction
from app.schemas.benefit import BenefitCreate, BenefitUpdate
from app.services.budget.benefit_generation import generate_benefit_transactions, reconcile_provisional
from app.services.budget.benefits import compute_states, create_benefit, update_benefit


def _courant(db):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db.add(acc)
    db.commit()
    return acc


def _benefit(db, account, **kw):
    data = {
        "name": "Prime d'activité", "organization": "CAF", "amount": 250.0, "payment_day": 5,
        "match_pattern": "CAF", "account_id": account.id, "auto_generate": True, "logo": "si:caf",
    }
    b = Benefit(**{**data, **kw})
    db.add(b)
    db.commit()
    return b


def _bank_entry(db, account, amount, when, merchant="VIR CAF DE PARIS"):
    t = Transaction(
        account_id=account.id, date=when, month_label=month_label_from_date(when), type="Entree",
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
    )
    db.add(t)
    db.commit()
    return t


def _generated(db):
    return db.query(Transaction).filter(Transaction.benefit_id.isnot(None)).all()


def test_generates_provisional_entry_on_payment_day(db_session):
    acc = _courant(db_session)
    benefit = _benefit(db_session, acc)

    assert generate_benefit_transactions(db_session, today=date(2026, 11, 5)) == 1

    [tx] = _generated(db_session)
    assert (tx.account_id, tx.type, tx.amount, tx.date) == (acc.id, "Entree", 250.0, datetime(2026, 11, 5))
    assert tx.benefit_id == benefit.id and tx.is_provisional is True
    assert tx.merchant == "Prime d'activité"
    assert tx.recurring_logo == "si:caf"
    assert tx.running_balance == 250.0  # soldes recalculés


def test_nothing_before_payment_day(db_session):
    _benefit(db_session, _courant(db_session))
    assert generate_benefit_transactions(db_session, today=date(2026, 11, 4)) == 0
    assert _generated(db_session) == []


def test_generation_is_idempotent(db_session):
    _benefit(db_session, _courant(db_session))
    generate_benefit_transactions(db_session, today=date(2026, 11, 5))
    assert generate_benefit_transactions(db_session, today=date(2026, 11, 20)) == 0
    assert len(_generated(db_session)) == 1


def test_skips_when_real_payment_already_received(db_session):
    acc = _courant(db_session)
    _benefit(db_session, acc)
    _bank_entry(db_session, acc, 243.12, datetime(2026, 11, 4))  # versé avant le jour habituel
    assert generate_benefit_transactions(db_session, today=date(2026, 11, 5)) == 0
    assert _generated(db_session) == []


def test_skips_inactive_manual_and_accountless_benefits(db_session):
    acc = _courant(db_session)
    _benefit(db_session, acc, active=False)
    _benefit(db_session, acc, name="APL", auto_generate=False)
    _benefit(db_session, acc, name="Sans compte", account_id=None)
    assert generate_benefit_transactions(db_session, today=date(2026, 11, 5)) == 0


def test_start_date_in_future_blocks_generation(db_session):
    _benefit(db_session, _courant(db_session), start_date=date(2026, 12, 1))
    assert generate_benefit_transactions(db_session, today=date(2026, 11, 5)) == 0


def test_provisional_entry_does_not_count_as_received(db_session):
    _benefit(db_session, _courant(db_session))
    generate_benefit_transactions(db_session, today=date(2026, 11, 12))
    [state] = compute_states(db_session, today=date(2026, 11, 12))
    assert state.status == "late" and state.payments == []


def test_real_payment_replaces_provisional(db_session):
    acc = _courant(db_session)
    benefit = _benefit(db_session, acc)
    generate_benefit_transactions(db_session, today=date(2026, 11, 5))
    real = _bank_entry(db_session, acc, 243.12, datetime(2026, 11, 6))

    assert reconcile_provisional(db_session) == 1

    db_session.expire_all()
    [only] = db_session.query(Transaction).filter(Transaction.account_id == acc.id).all()
    assert only.id == real.id and only.amount == 243.12 and only.is_provisional is False
    assert only.benefit_id == benefit.id  # le vrai versement hérite du logo
    assert only.running_balance == 243.12  # le doublon n'a pas faussé le solde
    [state] = compute_states(db_session, today=date(2026, 11, 7))
    assert state.status == "received"


def test_real_payment_too_far_keeps_provisional(db_session):
    acc = _courant(db_session)
    _benefit(db_session, acc)
    generate_benefit_transactions(db_session, today=date(2026, 11, 5))
    _bank_entry(db_session, acc, 250.0, datetime(2026, 10, 5))  # versement du mois précédent
    assert reconcile_provisional(db_session) == 0
    assert len(_generated(db_session)) == 1


def test_one_real_payment_replaces_only_one_provisional(db_session):
    acc = _courant(db_session)
    _benefit(db_session, acc, name="Prime", amount=250.0)
    _benefit(db_session, acc, name="APL", amount=180.0)
    generate_benefit_transactions(db_session, today=date(2026, 11, 5))
    _bank_entry(db_session, acc, 181.0, datetime(2026, 11, 5))
    assert reconcile_provisional(db_session) == 1
    [left] = [t for t in _generated(db_session) if t.is_provisional]
    assert left.merchant == "Prime"  # le versement le plus proche (APL, 180) a pris la sienne


def test_generating_benefit_requires_receiving_account(db_session):
    with pytest.raises(BusinessRuleError):
        create_benefit(db_session, BenefitCreate(
            name="Prime", organization="CAF", amount=250.0, match_pattern="CAF", auto_generate=True,
        ))
    acc = _courant(db_session)
    created = create_benefit(db_session, BenefitCreate(
        name="Prime", organization="CAF", amount=250.0, match_pattern="CAF",
        account_id=acc.id, auto_generate=True, logo="si:caf",
    ))
    assert created["logo"] == "si:caf" and created["auto_generate"] is True
    with pytest.raises(BusinessRuleError):
        update_benefit(db_session, created["id"], BenefitUpdate(account_id=None))


def test_csv_import_replaces_provisional_entry(client, db_session):
    acc = _courant(db_session)
    _benefit(db_session, acc)
    generate_benefit_transactions(db_session, today=date(2026, 11, 5))

    csv = "Date;Type;Commercant;Montant\n06/11/2026 00:00;Entrée;VIR CAF DE PARIS;243,12"
    resp = client.post(
        "/import/commit",
        data={"account_id": str(acc.id), "create_missing_categories": "true"},
        files={"file": ("import.csv", csv.encode("utf-8"), "text/csv")},
    )

    assert resp.status_code == 200 and resp.json()["imported"] == 1
    db_session.expire_all()
    [only] = db_session.query(Transaction).filter(Transaction.account_id == acc.id).all()
    assert (only.amount, only.is_provisional, only.merchant) == (243.12, False, "VIR CAF DE PARIS")
    assert only.running_balance == 243.12
