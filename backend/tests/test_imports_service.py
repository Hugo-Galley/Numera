"""Import CSV : caractérisation de bout en bout (écrite avant le découpage) et analyse pure."""
import json

from app.models.categorization_rule import CategorizationRule
from app.models.category import Category
from app.models.import_log import ImportLog
from app.models.transaction import Transaction

CSV = "\n".join([
    "Date;Type;Commercant;Categorie;Montant;Note",
    "05/01/2026;Sortie;CB CARREFOUR;Alimentation;42,50;",
    "06/01/2026;;LOYER JANVIER;Logement;-700;loyer",
    ";;;;;",
    "07/01/2026;Sortie;Boulangerie;Divers;3,20;",
    "07/01/2026;Sortie;Boulangerie;Divers;3,20;",
    "32/01/2026;Sortie;Erreur;Divers;1;",
    "08/01/2026;Entree;Salaire;Revenus;2500;",
])


def _post(client, account_id, csv=CSV, mapping=None):
    data = {"account_id": str(account_id), "create_missing_categories": "true"}
    if mapping is not None:
        data["category_mapping"] = json.dumps(mapping)
    files = {"file": ("releve.csv", csv.encode("utf-8"), "text/csv")}
    return client.post("/import/commit", data=data, files=files)


def test_commit_import_end_to_end(client, db_session):
    account_id = client.post("/accounts", json={"name": "Courant", "type": "courant", "currency": "EUR"}).json()["id"]
    courses = Category(name="Courses", type="depense")
    db_session.add(courses)
    db_session.commit()
    db_session.add(CategorizationRule(pattern="carrefour", category_id=courses.id, merchant_name="Carrefour"))
    db_session.commit()

    body = _post(client, account_id, mapping={"Logement": "CREATE", "Divers": courses.id}).json()
    assert {k: body[k] for k in ("imported", "skipped", "errors", "created_categories")} == {
        "imported": 5, "skipped": 0, "errors": 1, "created_categories": 2}
    assert body["error_details"][0]["line"] == 7 and "Date invalide" in body["error_details"][0]["reason"]

    db_session.expire_all()
    rows = db_session.query(Transaction).order_by(Transaction.date, Transaction.id).all()
    assert [(t.merchant, t.type, t.amount) for t in rows] == [
        ("Carrefour", "Sortie", 42.5), ("LOYER JANVIER", "Sortie", 700.0),
        ("Boulangerie", "Sortie", 3.2), ("Boulangerie", "Sortie", 3.2), ("Salaire", "Entree", 2500.0)]
    assert rows[0].category_id == courses.id and rows[2].category_id == courses.id
    assert {c.name for c in db_session.query(Category).all()} >= {"Logement", "Revenus"}
    assert [round(t.running_balance, 2) for t in rows] == [-42.5, -742.5, -745.7, -748.9, 1751.1]
    assert rows[1].note == "loyer" and rows[0].note == "Imported CSV"

    again = _post(client, account_id, mapping={"Logement": "CREATE", "Divers": courses.id}).json()
    assert (again["imported"], again["skipped"], again["errors"]) == (0, 5, 1)
    assert db_session.query(Transaction).count() == 5
    assert db_session.query(ImportLog).count() == 2


def test_commit_import_rejects_unknown_account_and_bad_mapping(client):
    assert _post(client, 999).status_code == 404
    account_id = client.post("/accounts", json={"name": "C", "type": "courant", "currency": "EUR"}).json()["id"]
    files = {"file": ("x.csv", CSV.encode(), "text/csv")}
    response = client.post("/import/commit", data={"account_id": str(account_id), "category_mapping": "{oops"}, files=files)
    assert response.status_code == 422 and response.json() == {"detail": "Invalid category_mapping JSON"}


def test_preview_reports_errors_and_repeats(client):
    files = {"file": ("releve.csv", CSV.encode("utf-8"), "text/csv")}
    body = client.post("/import/preview", data={"sample_size": "3"}, files=files).json()
    assert (body["total_rows"], body["invalid_rows"], body["delimiter"]) == (6, 1, ";")
    assert len(body["preview"]) == 3 and body["preview"][1]["Type"] == "Sortie"
    assert any("identique" in w for w in body["warnings"])
