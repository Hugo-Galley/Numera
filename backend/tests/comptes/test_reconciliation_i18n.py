"""Pistes du rapprochement bancaire dans la langue de l'interface (Accept-Language)."""
from datetime import datetime

import pytest

from app.core.i18n import set_language
from app.services.budget.balances import recalculate_running_balances
from tests.comptes.test_reconciliation import _setup, _tx

EN = {"Accept-Language": "en"}


@pytest.fixture(autouse=True)
def _reset_language():
    set_language("fr")
    yield
    set_language("fr")


def _hints(client, acc, bank_balance, headers=None):
    res = client.post(
        f"/accounts/{acc.id}/reconcile", json={"date": "2026-10-20", "bank_balance": bank_balance}, headers=headers or {}
    )
    assert res.status_code == 200, res.text
    return {h["kind"]: h["message"] for h in res.json()["hints"]}


def test_missing_hint_in_english(client, db_session):
    acc = _setup(db_session)
    recalculate_running_balances(db_session, acc.id)
    msg = _hints(client, acc, 1234.5, EN)["missing"]
    assert msg == "No line explains the gap: an entry of 84.50 EUR (or several) is probably missing before 2026-10-20."


def test_missing_hint_stays_french_without_header(client, db_session):
    acc = _setup(db_session)
    recalculate_running_balances(db_session, acc.id)
    msg = _hints(client, acc, 1234.5)["missing"]
    assert msg == "Aucune ligne n'explique l'écart : il manque probablement une entrée de 84,50 EUR (ou plusieurs) avant le 20/10/2026."


def test_extra_or_missing_and_wrong_sign_in_english(client, db_session):
    acc = _setup(db_session)
    recalculate_running_balances(db_session, acc.id)
    extra = _hints(client, acc, 950, EN)["extra_or_missing"]  # écart -200 : l'entrée « Virement Maman »
    assert extra == "“Virement Maman” (200.00 EUR) matches the gap exactly: extra line, or not yet posted by the bank at that date?"
    wrong = _hints(client, acc, 1250, EN)["wrong_sign"]  # écart +100 : la sortie Carrefour saisie dans le mauvais sens
    assert wrong == "“Carrefour” (50.00 EUR) was perhaps recorded the wrong way round (Sortie): reversing it would close the gap."


def test_duplicate_hint_in_english(client, db_session):
    acc = _setup(db_session)
    _tx(db_session, acc, "Sortie", 50, datetime(2026, 10, 6), "Carrefour")
    recalculate_running_balances(db_session, acc.id)
    msg = _hints(client, acc, 1150, EN)["duplicate"]
    assert msg == "Probable duplicate: “Carrefour” (50.00 EUR) appears twice and exactly explains the gap."
