from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.core.errors import InvalidOperationError
from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.transaction import Transaction
from app.services.budget import reimbursements as remb


def make_account(db: Session, name="Principal", currency="EUR", type_="courant"):
    acc = Account(name=name, type=type_, currency=currency, active=True)
    db.add(acc)
    db.commit()
    return acc


def tx(db: Session, account, type_, amount, date, merchant="x"):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency=account.currency, running_balance=0.0,
    )
    db.add(t)
    db.commit()
    return t


@pytest.fixture()
def resto(db_session: Session):
    main = make_account(db_session)
    sortie = tx(db_session, main, "Sortie", 90.0, datetime(2026, 9, 28), "RESTO LE PETIT")
    return main, sortie


def test_claim_and_allocation_update_offsets(db_session, resto):
    main, sortie = resto
    denis = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    remb.create_claim(db_session, sortie.id, "Julie", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3), "VIR DENIS")
    alloc = remb.allocate(db_session, denis, entree.id)
    assert alloc.amount == 30.0
    db_session.refresh(sortie)
    db_session.refresh(entree)
    assert sortie.reimbursement_offset == 30.0
    assert entree.reimbursement_offset == 30.0
    assert remb.claim_received(db_session, denis.id) == 30.0


def test_health_two_refunds_settle_one_claim(db_session, resto):
    main, _ = resto
    consult = tx(db_session, main, "Sortie", 30.0, datetime(2026, 9, 1), "DR MARTIN")
    claim = remb.create_claim(db_session, consult.id, "Sécu + mutuelle", 30.0)
    secu = tx(db_session, main, "Entree", 21.0, datetime(2026, 9, 6), "CPAM")
    mutuelle = tx(db_session, main, "Entree", 9.0, datetime(2026, 9, 12), "MUTUELLE")
    remb.allocate(db_session, claim, secu.id)
    remb.allocate(db_session, claim, mutuelle.id)
    assert remb.claim_received(db_session, claim.id) == 30.0
    db_session.refresh(consult)
    assert consult.reimbursement_offset == 30.0


def test_one_transfer_split_over_two_claims(db_session, resto):
    main, sortie = resto
    cine = tx(db_session, main, "Sortie", 40.0, datetime(2026, 9, 29), "CGR")
    c1 = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    c2 = remb.create_claim(db_session, cine.id, "Denis", 20.0)
    entree = tx(db_session, main, "Entree", 50.0, datetime(2026, 10, 3), "VIR DENIS")
    remb.allocate(db_session, c1, entree.id)
    remb.allocate(db_session, c2, entree.id)
    db_session.refresh(entree)
    assert entree.reimbursement_offset == 50.0
    with pytest.raises(InvalidOperationError) as exc:
        remb.allocate(db_session, c2, entree.id, 25.0)
    assert exc.value.status_code == 400


def test_reallocating_same_entree_updates_amount(db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id, 10.0)
    remb.allocate(db_session, claim, entree.id, 25.0)
    assert len(claim.allocations) == 1
    assert remb.claim_received(db_session, claim.id) == 25.0


def test_rules_are_enforced(db_session, resto):
    main, sortie = resto
    usd = make_account(db_session, "Revolut USD", "USD")
    entree_usd = tx(db_session, usd, "Entree", 30.0, datetime(2026, 10, 3))
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    cases = [
        lambda: remb.create_claim(db_session, entree.id, "X", 10.0),        # pas une Sortie
        lambda: remb.create_claim(db_session, sortie.id, "Julie", 70.0),    # 30 + 70 > 90
        lambda: remb.allocate(db_session, claim, sortie.id),                # pas une Entree
        lambda: remb.allocate(db_session, claim, entree_usd.id),            # devise différente
        lambda: remb.allocate(db_session, claim, entree.id, 31.0),          # > attendu
    ]
    for case in cases:
        with pytest.raises(InvalidOperationError) as exc:
            case()
        assert exc.value.status_code == 400
    remb.allocate(db_session, claim, entree.id, 20.0)
    with pytest.raises(InvalidOperationError):
        remb.update_claim(db_session, claim, {"expected_amount": 15.0})     # < reçu
    remb.update_claim(db_session, claim, {"expected_amount": 20.0, "debtor": "Denis M."})
    assert claim.expected_amount == 20.0 and claim.debtor == "Denis M."


def test_transfer_cannot_be_used(db_session, resto):
    main, sortie = resto
    sortie.is_transfer = True
    db_session.commit()
    with pytest.raises(InvalidOperationError):
        remb.create_claim(db_session, sortie.id, "Denis", 30.0)


def test_rounding_three_thirds(db_session, resto):
    main, _ = resto
    dep = tx(db_session, main, "Sortie", 99.99, datetime(2026, 9, 1))
    for name in ("A", "B", "C"):
        remb.create_claim(db_session, dep.id, name, 33.33)
    entree = tx(db_session, main, "Entree", 99.99, datetime(2026, 9, 2))
    db_session.refresh(dep)
    for c in dep.claims:
        remb.allocate(db_session, c, entree.id)
    db_session.refresh(dep)
    assert dep.reimbursement_offset == 99.99


def test_delete_claim_resets_offsets(db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id)
    remb.delete_claim(db_session, claim)
    db_session.refresh(sortie)
    db_session.refresh(entree)
    assert sortie.reimbursement_offset == 0.0 and entree.reimbursement_offset == 0.0


def test_api_flow(client, db_session, resto):
    main, sortie = resto
    r = client.post("/reimbursements/claims", json={"transaction_id": sortie.id, "debtor": "Denis", "expected_amount": 30})
    assert r.status_code == 201
    claim_id = r.json()["id"]
    client.post("/reimbursements/claims", json={"transaction_id": sortie.id, "debtor": "Julie", "expected_amount": 30})
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3), "VIR SEPA DENIS DUPONT")
    autre = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 2), "REMBOURSEMENT AMAZON")

    cands = client.get(f"/reimbursements/claims/{claim_id}/candidates").json()
    assert [c["id"] for c in cands][:2] == [entree.id, autre.id]  # débiteur dans le libellé d'abord
    assert cands[0]["available"] == 30.0

    body = client.post(f"/reimbursements/claims/{claim_id}/allocations", json={"entree_id": entree.id}).json()
    assert body["received"] == 30.0 and body["remaining"] == 0.0
    assert body["expense"]["id"] == sortie.id and body["allocations"][0]["entree_id"] == entree.id

    assert [c["debtor"] for c in client.get("/reimbursements/claims").json()] == ["Julie"]
    assert [c["debtor"] for c in client.get("/reimbursements/claims", params={"status": "settled"}).json()] == ["Denis"]
    summary = client.get("/reimbursements/summary").json()
    assert summary["total_due"] == 30.0
    assert summary["debtors"] == [{"debtor": "Julie", "claims": 1, "due": 30.0}]

    listed = client.get("/transactions", params={"account_id": main.id}).json()
    by_id = {t["id"]: t for t in listed}
    assert by_id[sortie.id]["has_claims"] is True and by_id[sortie.id]["reimbursement_offset"] == 30.0
    assert by_id[sortie.id]["reimbursement_expected"] == 60.0
    assert by_id[entree.id]["reimbursement_offset"] == 30.0

    for_entree = client.get(f"/reimbursements/entries/{autre.id}/claims").json()
    assert [c["debtor"] for c in for_entree["open_claims"]] == ["Julie"]
    assert for_entree["available"] == 30.0

    alloc_id = body["allocations"][0]["id"]
    assert client.delete(f"/reimbursements/allocations/{alloc_id}").status_code == 204
    assert client.patch(f"/reimbursements/claims/{claim_id}", json={"expected_amount": 25}).json()["expected_amount"] == 25.0
    assert client.delete(f"/reimbursements/claims/{claim_id}").status_code == 204
    assert client.post("/reimbursements/claims", json={"transaction_id": entree.id, "debtor": "X", "expected_amount": 5}).status_code == 400
    assert client.get("/reimbursements/claims/9999/candidates").status_code == 404


def test_guards_on_transaction_mutations(client, db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id)

    assert client.patch(f"/transactions/{sortie.id}", json={"amount": 20}).status_code == 400
    assert client.patch(f"/transactions/{entree.id}", json={"amount": 10}).status_code == 400
    assert client.patch(f"/transactions/{sortie.id}", json={"type": "Entree"}).status_code == 400
    assert client.patch("/transactions/bulk", json={"ids": [entree.id], "type": "Sortie"}).status_code == 400
    assert client.patch(f"/transactions/{sortie.id}", json={"is_transfer": True}).status_code == 400
    db_session.refresh(sortie)
    assert sortie.amount == 90.0 and sortie.type == "Sortie"
    assert client.patch(f"/transactions/{sortie.id}", json={"amount": 95}).status_code == 200


def test_deleting_entree_reopens_claim(client, db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id)
    assert client.delete(f"/transactions/{entree.id}").status_code == 204
    db_session.expire_all()
    assert db_session.get(Transaction, sortie.id).reimbursement_offset == 0.0
    assert [c["remaining"] for c in client.get("/reimbursements/claims").json()] == [30.0]


def test_deleting_sortie_frees_entree(client, db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id)
    assert client.delete(f"/transactions/{sortie.id}").status_code == 204
    db_session.expire_all()
    assert db_session.get(Transaction, entree.id).reimbursement_offset == 0.0
    assert client.get("/reimbursements/claims", params={"status": "all"}).json() == []


def test_reimbursement_excludes_transfer_matching(client, db_session, resto):
    main, sortie = resto
    livret = make_account(db_session, "Livret A", type_="epargne")
    remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    mirror = tx(db_session, livret, "Entree", 90.0, datetime(2026, 9, 28))
    assert client.get("/transactions/potential-transfers").json() == []
    assert client.post(f"/transactions/{sortie.id}/link/{mirror.id}").status_code == 400
    assert client.get(f"/transactions/{mirror.id}/transfer-candidates").json() == []


def test_categorization_apply_all_does_not_retype_reimbursed_transactions(client, db_session, resto):
    from app.models.categorization_rule import CategorizationRule
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id)
    db_session.add(CategorizationRule(pattern="resto", transaction_type="Entree", priority=1))
    db_session.commit()
    assert client.post("/categorization-rules/apply-all").status_code == 200
    db_session.expire_all()
    assert db_session.get(Transaction, sortie.id).type == "Sortie"


def _salary_setup(db_session, main):
    from datetime import date

    from app.models.recurring_transaction import RecurringTransaction
    from app.models.salary_config import SalaryConfig
    from app.models.salary_month import SalaryMonth
    rec = RecurringTransaction(account_id=main.id, name="Salaire", type="Entree", amount=2000.0,
                               frequency="monthly", start_date=datetime(2026, 1, 1))
    db_session.add(rec)
    db_session.commit()
    config = SalaryConfig(salary_account_id=main.id, net_salary=2000.0, ticket_value=10.0,
                          ticket_employee_share=5.0, salary_recurring_id=rec.id, is_active=True)
    db_session.add(config)
    db_session.commit()
    db_session.add(SalaryMonth(salary_config_id=config.id, month_label="2026-10", salary_date=date(2026, 10, 3), is_generated=True))
    salary = Transaction(
        account_id=main.id, date=datetime(2026, 10, 3), month_label="2026-10", type="Entree", merchant="Salaire",
        amount=2000.0, original_amount=2000.0, currency="EUR", running_balance=0.0,
        is_recurring=True, recurring_transaction_id=rec.id,
    )
    db_session.add(salary)
    db_session.commit()
    return salary


def test_salary_reset_resyncs_reimbursed_expense(client, db_session, resto):
    main, sortie = resto
    salary = _salary_setup(db_session, main)
    claim = remb.create_claim(db_session, sortie.id, "Employeur", 50.0)
    remb.allocate(db_session, claim, salary.id)
    salary_id, sortie_id = salary.id, sortie.id
    assert client.delete("/salary/generate/2026/10").status_code == 200
    db_session.expire_all()
    assert db_session.get(Transaction, salary_id) is None
    assert db_session.get(Transaction, sortie_id).reimbursement_offset == 0.0


def test_salary_telecommuting_cannot_drop_below_allocations(client, db_session, resto):
    main, sortie = resto
    salary = _salary_setup(db_session, main)
    big = tx(db_session, main, "Sortie", 3000.0, datetime(2026, 9, 1))
    claim = remb.create_claim(db_session, big.id, "Employeur", 2000.0)
    remb.allocate(db_session, claim, salary.id)
    r = client.put("/salary/telecommuting/2026/10", json={"dates": ["2026-10-05", "2026-10-06"]})
    assert r.status_code == 400
    db_session.expire_all()
    assert db_session.get(Transaction, salary.id).amount == 2000.0
