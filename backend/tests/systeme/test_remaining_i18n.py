"""Derniers textes de l'API dans la langue de l'interface : diversité, valorisation, import CSV, validations."""
from collections import Counter
from types import SimpleNamespace

import pytest

from app.core.i18n import set_language
from app.domain import csv_import
from app.domain.diversity import diversity_alerts, score_label
from app.services.budget.imports import _preview_warnings
from app.services.investissement.portfolio.compute import _performance

EN = {"Accept-Language": "en"}


@pytest.fixture(autouse=True)
def _reset_language():
    set_language("fr")
    yield
    set_language("fr")


def _company(name="ACME", pct=25.0, overlap=False):
    return {"name": name, "pct_stocks": pct, "pct_total_wealth": 10.0, "has_overlap": overlap}


def test_diversity_alerts_in_both_languages():
    fr = diversity_alerts([_company()], [], [])[0]
    assert fr["title"] == "Concentration critique sur ACME"
    assert fr["message"].startswith("ACME pèse 25.0% de votre portefeuille boursier (10.0% du patrimoine total).")
    set_language("en")
    en = diversity_alerts([_company(), _company("BETA", 12.0, overlap=True)], [], [])
    assert en[0]["title"] == "Critical concentration in ACME"
    assert en[1]["title"] == "High exposure to BETA"
    assert en[2]["title"] == "Overlapping exposure detected (1 securities)"
    assert en[0]["item_name"] == "ACME"  # donnée : jamais traduite


def test_geography_alerts_in_english():
    set_language("en")
    alerts = diversity_alerts([], [{"name": "USA", "percentage_stocks": 70.0}, {"name": "France", "percentage_stocks": 40.0}], [])
    assert [a["title"] for a in alerts] == ["Heavy US weighting (70.0%)", "French home bias (40.0%)"]


def test_score_label_follows_language():
    assert score_label(10) == "Concentration critique"
    set_language("en")
    assert score_label(10) == "Critical concentration" and score_label(90) == "Excellent diversification"


def test_valuation_warning_in_english():
    set_language("en")
    warnings: list[str] = []
    cap = SimpleNamespace(reference_value=0.0, external_total=100.0, reference=None, flow_events=[])
    _performance(cap, None, 0.0, 100.0, -50.0, "EUR", warnings)
    assert warnings == ["Negative cash: a deposit or sale is probably missing from the history."]


def test_import_preview_warnings_in_english():
    set_language("en")
    out = _preview_warnings([{"Type": ""}], Counter({"a": 2}))
    assert out[0] == "Type column missing: the direction is deduced from the amount's sign (negative = Sortie)."
    assert out[1].startswith("1 line(s) identical to another in the file")


def test_import_row_errors_in_english():
    set_language("en")
    with pytest.raises(csv_import.ImportRowError) as exc:
        csv_import.parse_row({"Date": "pas une date", "Montant": "1", "Commercant": "x"})
    assert str(exc.value) == "Invalid date “pas une date” (accepted formats: DD/MM/YYYY, YYYY-MM-DD)"
    set_language("fr")
    with pytest.raises(csv_import.ImportRowError) as exc:
        csv_import.parse_row({"Date": "pas une date", "Montant": "1", "Commercant": "x"})
    assert str(exc.value) == "Date invalide « pas une date » (formats acceptés : JJ/MM/AAAA, AAAA-MM-JJ)"


def test_schema_validation_message_follows_language(client):
    fr = client.post("/merchants", json={"name": " "})
    assert fr.status_code == 422 and "ne peut pas être vide" in fr.text
    en = client.post("/merchants", json={"name": " "}, headers=EN)
    assert en.status_code == 422 and "cannot be empty" in en.text

