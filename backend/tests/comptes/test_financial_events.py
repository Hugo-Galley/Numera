from app.models.account import Account
from app.models.financial_event import FinancialEvent


def _create(client, **payload):
    res = client.post("/financial-events", json={"date": "2026-09-15", "title": "Résiliation salle de sport", **payload})
    assert res.status_code == 201, res.text
    return res.json()


def test_create_and_list_most_recent_first(client, db_session):
    _create(client)
    _create(client, date="2026-10-01", title="  +200 €/mois sur le PEA  ", note="  ")
    events = client.get("/financial-events").json()
    assert [e["title"] for e in events] == ["+200 €/mois sur le PEA", "Résiliation salle de sport"]
    assert events[0]["note"] is None
    assert db_session.query(FinancialEvent).count() == 2


def test_filter_by_date_range(client):
    _create(client, date="2026-01-10")
    _create(client, date="2026-06-10")
    events = client.get("/financial-events?start=2026-03-01&end=2026-06-10").json()
    assert [e["date"] for e in events] == ["2026-06-10"]


def test_account_link_and_deleted_account(client, db_session):
    acc = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    event = _create(client, account_id=acc.id)
    assert event["account_name"] == "PEA"
    db_session.delete(acc)
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(FinancialEvent, event["id"]).account_id is None


def test_unknown_account_and_blank_title_are_rejected(client):
    assert client.post("/financial-events", json={"date": "2026-09-15", "title": "x", "account_id": 999}).status_code == 404
    assert client.post("/financial-events", json={"date": "2026-09-15", "title": "   "}).status_code == 422


def test_update_and_delete(client, db_session):
    event = _create(client)
    res = client.patch(f"/financial-events/{event['id']}", json={"title": "Résilié Basic-Fit", "note": "Économie 30 €/mois"})
    assert res.status_code == 200
    stored = db_session.get(FinancialEvent, event["id"])
    db_session.refresh(stored)
    assert stored.title == "Résilié Basic-Fit" and stored.note == "Économie 30 €/mois"
    assert client.delete(f"/financial-events/{event['id']}").status_code == 204
    db_session.expire_all()
    assert db_session.get(FinancialEvent, event["id"]) is None
    assert client.delete(f"/financial-events/{event['id']}").status_code == 404
