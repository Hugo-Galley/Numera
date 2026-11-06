"""Fiscalité (alertes d'enveloppe, conseil de placement, récap CTO) dans la langue de l'interface."""
from datetime import date

import pytest

from app.core.i18n import set_language
from app.domain.tax import (
    PeeLot,
    allocation_advice,
    av_status,
    ldds_status,
    lep_status,
    livret_a_status,
    pea_status,
    pee_status,
    per_status,
)
from app.domain.tax_rules import rules_for

RULES = rules_for(2026)
TODAY = date(2026, 6, 15)
EN = {"Accept-Language": "en"}


@pytest.fixture(autouse=True)
def _reset_language():
    set_language("fr")
    yield
    set_language("fr")


def test_pea_alerts_in_english():
    set_language("en")
    missing = pea_status(1_000, None, [], TODAY, RULES)
    assert missing["alerts"] == ["Opening date missing: enter it in the account settings."]
    early = pea_status(1_000, date(2024, 1, 1), [date(2025, 1, 1)], TODAY, RULES)
    assert early["alerts"] == ["Withdrawal before 5 years: the PEA's favourable tax treatment is lost."]
    over = pea_status(RULES.pea_ceiling + 1, date(2015, 1, 1), [], TODAY, RULES)
    assert over["alerts"] == ["PEA contribution ceiling exceeded."]


def test_pea_alerts_stay_french_by_default():
    assert pea_status(1_000, None, [], TODAY, RULES)["alerts"] == ["Date d'ouverture manquante : renseigne-la dans les paramètres du compte."]


def test_per_and_savings_alerts_in_english():
    set_language("en")
    assert per_status(5_000, 20_000, 30, RULES)["alerts"] == ["Contributions above the deduction ceiling: the excess is not deductible."]
    assert livret_a_status(RULES.livret_a_ceiling + 1, RULES)["alerts"] == [
        "Livret A contribution ceiling reached: capitalised interest may legitimately exceed it."]
    assert lep_status(500, RULES)["alerts"] == [
        "The LEP is reserved for households under an income ceiling: check again every year (not verified here)."]
    assert "LDDS" in ldds_status(RULES.ldds_ceiling + 1, RULES)["alerts"][0]


def test_pee_and_av_alerts_in_english():
    set_language("en")
    no_salary = pee_status([PeeLot(date(2026, 1, 1), 500.0, False)], 0.0, 0.0, TODAY, RULES)
    assert no_salary["alerts"] == ["Enter your gross annual salary in the settings to track the voluntary contribution ceiling."]
    assert av_status(None, "single", TODAY, RULES)["alerts"] == ["Opening date missing: enter it in the account settings."]


def _card(kind, remaining, account_id=1, name=None):
    return {"kind": kind, "account_id": account_id, "account_name": name or kind.upper(), "remaining": remaining}


def test_allocation_advice_in_english():
    set_language("en")
    steps = allocation_advice([_card("livret_a", 20_000, 1), _card("pea", 50_000, 3)], 4.5, 41)
    assert steps[0]["reason"] == (
        "Your emergency savings cover 4.5 months of expenses, the target is 6 months: "
        "pay into your Livret A, available at any time and tax-free.")
    assert steps[1]["reason"].startswith("Long-term equities: the PEA is exempt from tax on gains after 5 years")
    assert steps[2]["reason"] == "With a 41% bracket, a PER would reduce your tax (money locked until retirement)."
    assert steps[2]["account_name"] == "PER to open"
    assert steps[3]["account_name"] == "Life insurance to open"


def test_allocation_advice_in_french_keeps_decimal_comma():
    steps = allocation_advice([_card("livret_a", 20_000, 1)], 4.5, None)
    assert steps[0]["reason"].startswith("Ton épargne de précaution couvre 4,5 mois de dépenses")


def test_overview_alerts_follow_accept_language(client):
    resp = client.post("/accounts", json={"name": "Mon PEA", "type": "investissement", "currency": "EUR", "color": None, "tax_wrapper": "pea"})
    assert resp.status_code == 201, resp.text
    fr_alerts = [a for card in client.get("/tax/overview").json()["wrappers"] for a in card["alerts"]]
    en_alerts = [a for card in client.get("/tax/overview", headers=EN).json()["wrappers"] for a in card["alerts"]]
    assert "Date d'ouverture manquante : renseigne-la dans les paramètres du compte." in fr_alerts
    assert "Opening date missing: enter it in the account settings." in en_alerts


def test_cto_report_warning_in_english(client, monkeypatch):
    """Récap CTO : avertissement « vente sans coût de revient » dans la langue de la requête."""
    from types import SimpleNamespace

    import app.services.investissement.tax as tax_service

    cto = client.post("/accounts", json={"name": "Mon CTO", "type": "investissement", "currency": "EUR", "color": None, "tax_wrapper": "cto"}).json()

    async def fake_replay(db, account_id):
        sale = SimpleNamespace(date=date(2025, 3, 3), realized_eur=None, ticker="AAA", cost_eur_estimated=False)
        return SimpleNamespace(realized=[sale])

    async def no_dividends(db, account_id):
        return []

    monkeypatch.setattr(tax_service, "replay_account", fake_replay)
    monkeypatch.setattr(tax_service, "load_dividends_eur", no_dividends)
    url = "/tax/annual-report?year=2025"
    assert client.get(url).json()["warnings"] == ["Mon CTO : 1 vente(s) sans coût de revient connu, plus-value non comptée."]
    assert client.get(url, headers=EN).json()["warnings"] == ["Mon CTO: 1 sale(s) without a known cost basis, capital gain not counted."]
    assert cto["id"]
