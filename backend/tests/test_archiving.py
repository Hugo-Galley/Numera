from app.models.category import Category
from app.models.tag import Tag


def test_archived_category_hidden_from_pickers_only(client, db_session):
    a = client.post("/categories", json={"name": "Ancienne", "type": "depense"}).json()
    client.post("/categories", json={"name": "Courses", "type": "depense"})

    res = client.patch(f"/categories/{a['id']}", json={"archived": True})
    assert res.status_code == 200 and res.json()["archived"] is True
    assert db_session.get(Category, a["id"]).archived is True

    names_all = {c["name"] for c in client.get("/categories").json()}
    names_active = {c["name"] for c in client.get("/categories", params={"include_archived": False}).json()}
    assert "Ancienne" in names_all
    assert "Ancienne" not in names_active and "Courses" in names_active

    # null = ne pas modifier
    assert client.patch(f"/categories/{a['id']}", json={"archived": None}).json()["archived"] is True


def test_archived_tag(client, db_session):
    t = client.post("/tags", json={"name": "Voyage 2023", "color": "#ff0000"}).json()
    assert client.patch(f"/tags/{t['id']}", json={"archived": True}).json()["archived"] is True
    assert db_session.get(Tag, t["id"]).archived is True
    assert client.get("/tags", params={"include_archived": False}).json() == []
    assert len(client.get("/tags").json()) == 1
