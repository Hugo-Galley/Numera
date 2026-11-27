"""Derniers textes de l'API dans la langue de l'interface : diversité, valorisation, import CSV, validations."""
from collections import Counter
from types import SimpleNamespace

import pytest

from app.core.i18n import set_language
from app.domain import csv_import
from app.domain.diversity_score import score_label
from app.domain.exposure.alerts import market_alerts
from app.domain.exposure.market_gap import DimensionGap, GapRow
from app.services.budget.imports import _preview_warnings
from app.services.investissement.portfolio.compute import _performance

EN = {"Accept-Language": "en"}


@pytest.fixture(autouse=True)
def _reset_language():
    set_language("fr")
    yield
    set_language("fr")


def test_diversity_alerts_in_both_languages():
    gaps = {"sectors": DimensionGap(10.0, 100.0, (GapRow("Technologie", 38.0, 25.0, False, 13.0),))}
    fr = market_alerts(gaps, [], {}, [], ["ACME"])
    assert fr[0]["title"] == "Sur-pondération : Technologie (38,0 %)"
    assert fr[0]["message"] == ("Technologie pèse 38,0 % de ta part connue, contre 25,0 % pour le marché de "
                                "référence.")
    set_language("en")
    en = market_alerts(gaps, [], {}, [], ["ACME"])
    assert en[0]["title"] == "Overweight: Technologie (38.0%)"
    assert en[1]["title"] == "Overlapping exposure detected (1 securities)"
    assert en[0]["item_name"] == "Technologie"  # donnée : jamais traduite


def test_score_without_reference_follows_language():
    from app.core.i18n import tr
    assert tr("diversity.score_no_reference") == "Référence de marché indisponible : score neutre"
    set_language("en")
    assert tr("diversity.score_no_reference") == "Market reference unavailable: neutral score"


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

