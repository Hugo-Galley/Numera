from datetime import date, datetime

from app.domain.benefits import advance_declaration, assign, month_status, next_payment_date
from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.benefit import Benefit
from app.models.transaction import Transaction
from app.services.audit.context import AuditContext
from app.services.audit.rules import benefits as rule
from app.services.budget.benefits import benefits_summary, compute_states, to_read


def _entry(db, account, amount, when, merchant="VIR CAF DE PARIS", is_transfer=False):
    t = Transaction(
        account_id=account.id, date=when, month_label=month_label_from_date(when), type="Entree",
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
        is_transfer=is_transfer,
    )
    db.add(t)
    db.commit()
    return t


def _courant(db):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db.add(acc)
    db.commit()
    return acc


def _benefit(db, **kw):
    data = {"name": "Prime d'activité", "organization": "CAF", "amount": 250.0, "payment_day": 5, "match_pattern": "CAF"}
    b = Benefit(**{**data, **kw})
    db.add(b)
    db.commit()
    return b


def test_month_status_window():
    # Versé le 3 (avant le 5 habituel) : reçu
    assert month_status(date(2026, 11, 4), 5, [date(2026, 11, 3)])[0] == "received"
    # Versement du mois précédent : ne compte pas pour ce mois
    assert month_status(date(2026, 11, 12), 5, [date(2026, 10, 5)]) == ("late", date(2026, 11, 5))
    assert month_status(date(2026, 11, 8), 5, [])[0] == "pending"
    # Aide qui démarre après la date attendue : jamais en retard ce mois-ci
    assert month_status(date(2026, 11, 20), 5, [], start=date(2026, 11, 15))[0] == "pending"
    assert next_payment_date(date(2026, 11, 12), 5, "late") == date(2026, 12, 5)
    assert next_payment_date(date(2026, 11, 2), 5, "pending") == date(2026, 11, 5)


def test_advance_declaration_skips_past_deadlines():
    assert advance_declaration(date(2026, 10, 31), 3, date(2026, 10, 29)) == date(2027, 1, 31)
    # Déclaration oubliée deux trimestres : la prochaine échéance est dans le futur
    assert advance_declaration(date(2026, 1, 31), 3, date(2026, 10, 29)) == date(2026, 10, 31)


def test_assign_closest_amount():
    assert assign({1: [10, 20], 2: [10]}, {1: 180.0, 2: 250.0}, {10: 250.0, 20: 175.0}) == {1: 20, 2: 10}


def test_payments_matched_and_split_between_benefits(db_session):
    acc = _courant(db_session)
    prime = _benefit(db_session)
    apl = _benefit(db_session, name="APL", amount=180.0)
    _entry(db_session, acc, 252.0, datetime(2026, 11, 5))
    _entry(db_session, acc, 180.0, datetime(2026, 11, 5))
    _entry(db_session, acc, 999.0, datetime(2026, 11, 5), merchant="CAF", is_transfer=True)
    _entry(db_session, acc, 50.0, datetime(2026, 11, 6), merchant="REMBOURSEMENT AMELI")

    states = {st.benefit.id: st for st in compute_states(db_session, date(2026, 11, 10))}

    assert [t.amount for t in states[prime.id].payments] == [252.0]
    assert [t.amount for t in states[apl.id].payments] == [180.0]
    assert states[prime.id].status == "received"
    read = to_read(states[prime.id], date(2026, 11, 10))
    assert read["received_this_year"] == 252.0
    assert read["amount_changed"] is False


def test_account_filter_and_start_date(db_session):
    acc = _courant(db_session)
    other = Account(name="Livret", type="epargne", currency="EUR", active=True)
    db_session.add(other)
    db_session.commit()
    b = _benefit(db_session, account_id=acc.id, start_date=date(2026, 10, 1))
    _entry(db_session, other, 250.0, datetime(2026, 11, 5))
    _entry(db_session, acc, 250.0, datetime(2026, 9, 5))

    [st] = compute_states(db_session, date(2026, 11, 20))

    assert st.payments == []
    assert st.status == "late"
    assert st.benefit.id == b.id


def test_action_center_rules(db_session):
    acc = _courant(db_session)
    _benefit(db_session, declaration_interval_months=3, next_declaration_date=date(2026, 11, 14))
    _entry(db_session, acc, 310.0, datetime(2026, 10, 5))

    actions = {a.id.split("-")[1]: a for a in rule.detect(AuditContext(db=db_session, now=datetime(2026, 11, 12)))}

    assert actions.keys() == {"declaration", "late", "amount"}
    assert actions["declaration"].id.endswith("2026-11-14")
    assert actions["declaration"].severity == "medium"
    assert actions["late"].id.endswith("2026-11")
    assert actions["amount"].severity == "low"


def test_inactive_benefit_raises_nothing(db_session):
    _benefit(db_session, active=False, declaration_interval_months=3, next_declaration_date=date(2026, 11, 1))
    assert rule.detect(AuditContext(db=db_session, now=datetime(2026, 11, 20))) == []


def test_summary(db_session):
    acc = _courant(db_session)
    _benefit(db_session, declaration_interval_months=3, next_declaration_date=date(2027, 1, 31))
    _entry(db_session, acc, 250.0, datetime(2026, 10, 5))
    _entry(db_session, acc, 250.0, datetime(2026, 11, 5))

    s = benefits_summary(db_session, date(2026, 11, 10))

    assert s["monthly_expected_total"] == 250.0
    assert s["received_this_year"] == 500.0
    assert s["late_count"] == 0
    assert s["next_declaration"]["declaration_days_left"] == 82


def test_crud_and_declared(client, db_session):
    acc = _courant(db_session)
    res = client.post("/benefits", json={
        "name": "Prime d'activité", "organization": "CAF", "amount": 250, "match_pattern": "CAF",
        "account_id": acc.id, "declaration_interval_months": 3, "next_declaration_date": "2026-10-31",
    })
    assert res.status_code == 201, res.text
    benefit_id = res.json()["id"]

    res = client.post(f"/benefits/{benefit_id}/declared", json={"amount": 275})
    assert res.status_code == 200, res.text
    db_session.expire_all()
    stored = db_session.get(Benefit, benefit_id)
    assert stored.amount == 275
    assert stored.next_declaration_date > date(2026, 10, 31)

    assert client.patch(f"/benefits/{benefit_id}", json={"declaration_interval_months": None}).status_code == 422
    assert client.patch(f"/benefits/{benefit_id}", json={"payment_day": 6}).json()["payment_day"] == 6
    assert client.get("/benefits").json()[0]["account_name"] == "Courant"
    assert client.get("/benefits/summary").status_code == 200

    assert client.delete(f"/benefits/{benefit_id}").status_code == 204
    assert db_session.get(Benefit, benefit_id) is None


def test_declared_requires_declaration(client):
    res = client.post("/benefits", json={"name": "APL", "organization": "CAF", "amount": 180, "match_pattern": "CAF"})
    assert client.post(f"/benefits/{res.json()['id']}/declared", json={}).status_code == 422
