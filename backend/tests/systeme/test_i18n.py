"""Textes du backend dans la langue de l'interface : en-tête Accept-Language, catalogues fr/en, repli."""
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.i18n import LANGUAGES, LanguageMiddleware, get_language, load_catalog, set_language, tr, trn
from app.domain.insights import eur, health_score


@pytest.fixture(autouse=True)
def _reset_language():
    set_language("fr")
    yield
    set_language("fr")


def test_default_language_is_french():
    assert get_language() == "fr"
    assert tr("insights.health.savings_rate") == "Taux d'Épargne"


def test_tr_follows_current_language():
    set_language("en")
    assert tr("insights.health.savings_rate") == "Savings rate"
    set_language("es")
    assert tr("insights.health.savings_rate") == "Tasa de ahorro"


def test_unknown_language_falls_back_to_french():
    set_language("de")
    assert get_language() == "fr"


def test_unknown_key_is_returned_as_is_not_raised():
    assert tr("does.not.exist") == "does.not.exist"


def test_tr_interpolates_parameters():
    set_language("en")
    assert "€1,234.50" in tr("insights.subscription_increase.description", amount=eur(1234.5))


def test_trn_picks_plural_form(monkeypatch):
    monkeypatch.setitem(load_catalog("en"), "t.items_one", "{count} item")
    monkeypatch.setitem(load_catalog("en"), "t.items_other", "{count} items")
    monkeypatch.setitem(load_catalog("fr"), "t.items_one", "{count} élément")
    monkeypatch.setitem(load_catalog("fr"), "t.items_other", "{count} éléments")
    set_language("en")
    assert (trn("t.items", 1), trn("t.items", 0), trn("t.items", 3)) == ("1 item", "0 items", "3 items")
    set_language("fr")
    assert (trn("t.items", 0), trn("t.items", 1), trn("t.items", 2)) == ("0 élément", "1 élément", "2 éléments")


def test_eur_follows_language():
    assert eur(1234.5) == "1\u202f234,50\u00a0€"
    set_language("en")
    assert eur(1234.5) == "€1,234.50"


def test_health_score_metric_names_are_translated():
    budget = {"taux_epargne": 25.0, "revenus_totaux": 3000.0, "depenses_reelles": 2000.0, "investissements_du_mois": 400.0}
    assert [m.name for m in health_score(budget, 8.0).metrics][:2] == ["Taux d'Épargne", "Fonds de Sécurité"]
    set_language("en")
    metrics = health_score(budget, 8.0).metrics
    assert [m.name for m in metrics] == ["Savings rate", "Emergency fund", "Cash flow", "Investment ratio"]
    assert metrics[1].unit == "mois"  # code d'unité stable : le frontend la traduit


def _app() -> TestClient:
    app = FastAPI()
    app.add_middleware(LanguageMiddleware)

    @app.get("/lang")
    def lang():
        return {"lang": get_language()}

    return TestClient(app)


@pytest.mark.parametrize(
    ("header", "expected"),
    [(None, "fr"), ("fr", "fr"), ("en", "en"), ("en-GB,en;q=0.9", "en"), ("EN-us", "en"), ("es-ES,es;q=0.9", "es"), ("de,en;q=0.5", "fr"), ("", "fr")],
)
def test_middleware_reads_accept_language(header, expected):
    headers = {"Accept-Language": header} if header is not None else {}
    assert _app().get("/lang", headers=headers).json() == {"lang": expected}


def test_language_does_not_leak_between_requests():
    client = _app()
    assert client.get("/lang", headers={"Accept-Language": "en"}).json() == {"lang": "en"}
    assert client.get("/lang").json() == {"lang": "fr"}


@pytest.mark.parametrize("language", [code for code in LANGUAGES if code != "fr"])
def test_catalogs_have_the_same_keys_and_placeholders(language):
    fr, other = load_catalog("fr"), load_catalog(language)
    assert set(fr) == set(other), sorted(set(fr) ^ set(other))
    var = re.compile(r"\{(\w+)\}")
    for key in fr:
        assert other[key].strip(), key
        assert set(var.findall(fr[key])) == set(var.findall(other[key])), key


def test_supported_languages():
    assert LANGUAGES == ("fr", "en", "es")


def test_route_answers_in_the_language_of_the_request(client):
    """Bout en bout : l'en-tête traverse le middleware jusqu'au calcul (scénarios de la projection FIRE)."""
    query = "/analytics/fire?monthly_savings=500&annual_expenses=24000"
    fr_labels = [s["label"] for s in client.get(query).json()["scenarios"]]
    en_labels = [s["label"] for s in client.get(query, headers={"Accept-Language": "en"}).json()["scenarios"]]
    assert fr_labels == ["Actuel", "+100 €/mois", "+250 €/mois", "+500 €/mois", "Dépenses −10 %"]
    assert en_labels == ["Current", "+€100/month", "+€250/month", "+€500/month", "Expenses −10%"]


# --- Formats par langue : ajouter une langue ne demande qu'une entrée de table, un catalogue et un code ---

def test_every_language_has_formats_and_catalog():
    from app.core.i18n import FORMATS, LANGUAGES, load_catalog

    assert set(FORMATS) == set(LANGUAGES)
    assert all(load_catalog(code) for code in LANGUAGES)


def test_number_money_and_date_formats():
    from datetime import date, datetime

    from app.core.i18n import format_date, format_datetime, format_money, format_number, set_language

    set_language("fr")
    assert format_number(1234.5) == "1 234,50"
    assert format_number(2.5, 1, thousands="") == "2,5"
    assert format_money(1234.5) == "1 234,50 €"
    assert format_money(1234.5, gap=" ") == "1 234,50 €"
    assert format_date(date(2026, 10, 20)) == "20/10/2026"
    assert format_datetime(datetime(2026, 10, 20, 9, 5)) == "20/10/2026 09:05"
    set_language("en")
    assert format_number(1234.5) == "1,234.50" and format_number(2.5, 1, thousands="") == "2.5"
    assert format_money(1234.5) == "€1,234.50"
    assert format_date(date(2026, 10, 20)) == "2026-10-20"
    assert format_datetime(datetime(2026, 10, 20, 9, 5)) == "2026-10-20 09:05"
    set_language("es")
    assert format_number(1234.5) == "1.234,50" and format_number(2.5, 1, thousands="") == "2,5"
    assert format_money(1234.5) == "1.234,50\u00a0€"
    assert format_date(date(2026, 10, 20)) == "20/10/2026"
    assert format_datetime(datetime(2026, 10, 20, 9, 5)) == "20/10/2026 09:05"
    set_language("fr")


def test_new_language_only_needs_a_formats_entry(monkeypatch):
    import app.core.i18n as i18n

    monkeypatch.setattr(i18n, "LANGUAGES", ("fr", "en", "xx"))
    monkeypatch.setitem(i18n.FORMATS, "xx", i18n.Formats(",", ".", ".", False, " ", "%d.%m.%Y", "%d.%m.%Y %H:%M", False))
    i18n.set_language("xx")
    try:
        assert i18n.format_number(1234.5) == "1.234,50"
        assert i18n.format_money(5) == "5,00 €"
    finally:
        i18n.set_language("fr")


def test_notification_language_schema_matches_supported_languages():
    """Le schéma des réglages de notification énumère les langues : à garder aligné sur LANGUAGES."""
    from typing import get_args

    from app.core.i18n import LANGUAGES
    from app.schemas.notification import NotificationSettingsRead

    assert set(get_args(NotificationSettingsRead.model_fields["language"].annotation)) == set(LANGUAGES)
