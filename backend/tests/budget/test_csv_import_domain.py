"""Analyse CSV pure (sans base) : montants, en-têtes, délimiteur, lignes."""
import pytest

from app.core.errors import BusinessRuleError
from app.domain.csv_import import ImportRowError, normalize_header, parse_amount, parse_csv, parse_row


def test_parse_amount_accepts_french_format():
    assert parse_amount("1 234,56") == 1234.56


def test_parse_amount_keeps_sign():
    assert parse_amount("-12,50 €") == -12.5


def test_normalize_header_maps_accents_and_spaces():
    assert normalize_header("Commerçant ou bénéficiaire") == "commercantoubeneficiaire"


def test_parse_csv_detects_semicolon_and_canonical_headers():
    rows, delimiter, headers = parse_csv("Date;Commerçant;Montant\n01/02/2026;Café;-2,10\n".encode())
    assert delimiter == ";" and headers == ["Date", "Commerçant", "Montant"]
    assert rows[0]["Commercant"] == "Café" and rows[0]["_line"] == "2"


def test_parse_csv_without_amount_column_is_rejected():
    with pytest.raises(BusinessRuleError, match="Colonnes manquantes dans le fichier : Montant"):
        parse_csv(b"Date;Commercant\n01/02/2026;Cafe\n")


def test_parse_row_infers_type_from_sign():
    row = {"_line": "3", "Date": "01/02/2026", "Commercant": "", "Montant": "-5", "Type": ""}
    parsed = parse_row(row)
    assert (parsed.type, parsed.amount, parsed.merchant, parsed.line) == ("Sortie", 5.0, "Inconnu", 3)


def test_parse_row_rejects_zero_without_type():
    with pytest.raises(ImportRowError, match="Type absent et montant nul"):
        parse_row({"_line": "2", "Date": "01/02/2026", "Commercant": "x", "Montant": "0"})
