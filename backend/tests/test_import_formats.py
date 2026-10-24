"""Lot 4 de l'audit : formats d'import (B4, B5, B11) et retour d'erreurs ligne par ligne (U1)."""
import pytest

from app.api.imports import _parse_amount
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1,234.50", 1234.5),        # format anglais : le décimal est le dernier séparateur
        ("1.234,50", 1234.5),        # format français
        ("1 234,56", 1234.56),
        ("1 234,56 €", 1234.56),
        ("12,50", 12.5),
        ("12.50", 12.5),
        ("1.234.567,89", 1234567.89),
        ("1,234,567.89", 1234567.89),
        ("-12,50", -12.5),
        ("-1,234.50", -1234.5),
        ("+2000", 2000.0),
    ],
)
def test_parse_amount_handles_both_locales_and_signs(raw, expected):
    assert _parse_amount(raw) == pytest.approx(expected)


@pytest.fixture
def account(db_session):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    return acc


def _commit(client, account, csv_text, **data):
    files = {"file": ("import.csv", csv_text.encode("utf-8"), "text/csv")}
    payload = {"account_id": str(account.id), "create_missing_categories": "true", **data}
    return client.post("/import/commit", data=payload, files=files)


def test_month_column_is_optional(client, db_session, account):
    csv_text = "Date;Type;Commercant;Categorie;Montant\n03/01/2026;Sortie;KFC;Nourriture;12,50\n"
    r = _commit(client, account, csv_text)
    assert r.status_code == 200 and r.json()["imported"] == 1
    assert db_session.query(Transaction).one().month_label == "Janvier"


def test_signed_amounts_without_type_column(client, db_session, account):
    csv_text = (
        "Date;Libelle;Commercant;Montant\n"
        "03/01/2026;x;Boulangerie;-12,50\n"
        "04/01/2026;x;Employeur;2000,00\n"
    ).replace("Libelle", "Note")
    r = _commit(client, account, csv_text)
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 2
    rows = {t.merchant: (t.type, t.amount) for t in db_session.query(Transaction).all()}
    assert rows["Boulangerie"] == ("Sortie", 12.5)
    assert rows["Employeur"] == ("Entree", 2000.0)


def test_explicit_type_wins_over_amount_sign(client, db_session, account):
    csv_text = "Date;Type;Commercant;Categorie;Montant\n03/01/2026;Sortie;KFC;Nourriture;-12,50\n"
    assert _commit(client, account, csv_text).json()["imported"] == 1
    tx = db_session.query(Transaction).one()
    assert (tx.type, tx.amount) == ("Sortie", 12.5)


def test_blank_lines_are_not_errors(client, account):
    csv_text = (
        "Date;Mois;Type;Commercant;Categorie;Montant\n"
        "03/01/2026;Janvier;Sortie;KFC;Nourriture;12,50\n"
        ";;;;;\n"
        "\n"
    )
    body = _commit(client, account, csv_text).json()
    assert body["imported"] == 1 and body["errors"] == 0


def test_zero_initial_balance_is_accepted_but_zero_expense_is_not(client, db_session, account):
    csv_text = (
        "Date;Mois;Type;Commercant;Categorie;Montant\n"
        "01/01/2026;Janvier;Solde Initial;Banque;Divers;0\n"
        "03/01/2026;Janvier;Sortie;KFC;Nourriture;0\n"
    )
    body = _commit(client, account, csv_text).json()
    assert body["imported"] == 1 and body["errors"] == 1
    assert db_session.query(Transaction).one().type == "Solde Initial"


def test_all_duplicates_file_creates_no_category(client, db_session, account):
    first = "Date;Mois;Type;Commercant;Categorie;Montant\n03/01/2026;Janvier;Sortie;KFC;Nourriture;12,50\n"
    _commit(client, account, first)
    second = (
        "Date;Mois;Type;Commercant;Categorie;Montant\n"
        "03/01/2026;Janvier;Sortie;KFC;Nourriture;12,50\n"
    )
    # même ligne, autre catégorie CSV : doublon, la catégorie ne doit pas être créée
    second = second.replace("Nourriture", "CategorieFantome")
    body = _commit(client, account, second).json()
    assert body["skipped"] == 1 and body["imported"] == 0
    assert db_session.query(Category).filter_by(name="CategorieFantome").count() == 0


def test_commit_reports_each_invalid_line_in_french(client, account):
    csv_text = (
        "Date;Mois;Type;Commercant;Categorie;Montant\n"
        "31/02/2026;Février;Sortie;KFC;Nourriture;12,50\n"
        "03/01/2026;Janvier;Sortie;KFC;Nourriture;abc\n"
        "04/01/2026;Janvier;Sortie;KFC;Nourriture;5,00\n"
    )
    body = _commit(client, account, csv_text).json()
    assert body["imported"] == 1 and body["errors"] == 2
    details = body["error_details"]
    assert [d["line"] for d in details] == [2, 3]  # ligne 1 = en-têtes
    assert all(isinstance(d["reason"], str) and d["reason"] for d in details)
    assert "date" in details[0]["reason"].lower()
    assert "montant" in details[1]["reason"].lower()


def test_preview_flags_invalid_rows(client, account):
    csv_text = (
        "Date;Mois;Type;Commercant;Categorie;Montant\n"
        "31/02/2026;Février;Sortie;KFC;Nourriture;12,50\n"
        "04/01/2026;Janvier;Sortie;KFC;Nourriture;5,00\n"
    )
    files = {"file": ("x.csv", csv_text.encode(), "text/csv")}
    body = client.post("/import/preview", data={"account_id": str(account.id)}, files=files).json()
    assert body["invalid_rows"] == 1
    assert body["preview"][0]["error"] and body["preview"][1]["error"] is None
    assert body["preview"][1]["Type"] == "Sortie"
