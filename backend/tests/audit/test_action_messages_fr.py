"""Textes du Centre d'Actions et des insights en français : tutoiement, accords, accents, montants « 61,00 € »."""
import asyncio
import json
import re
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.i18n import set_language, trn
from app.services.audit import context as audit_context
from app.services.audit.rules import budget, subscription_prices

FR = json.loads((Path(__file__).resolve().parents[2] / "app" / "core" / "locales" / "fr.json").read_text(encoding="utf-8"))
USER_TEXTS = {k: v for k, v in FR.items() if k.startswith(("audit.", "insights."))}
UNACCENTED = re.compile(
    r"\b(categories?|depenses?|meme|regles|etre|verifier|inutilisees|obsoletes|rafraichies|rapproches|conserve|marche)\b",
    re.IGNORECASE,
)


@pytest.fixture(autouse=True)
def _french():
    set_language("fr")
    yield
    set_language("fr")


def test_french_texts_use_tu():
    offenders = {k: v for k, v in USER_TEXTS.items() if re.search(r"\b(vous|votre|vos|archivez)\b", v, re.IGNORECASE)}
    assert offenders == {}


def test_french_texts_have_no_frozen_plural_or_missing_accents():
    assert {k: v for k, v in USER_TEXTS.items() if "(s)" in v} == {}
    assert {k: v for k, v in USER_TEXTS.items() if UNACCENTED.search(v)} == {}


@pytest.mark.parametrize(("key", "one", "other"), [
    ("audit.stale_snapshots.description", "1 compte d'investissement n'a pas", "3 comptes d'investissement n'ont pas"),
    ("audit.uncategorized.description", "1 dépense sans catégorie", "3 dépenses sans catégorie"),
    ("audit.unallocated_reimbursements.description", "1 remboursement reçu n'est rattaché", "3 remboursements reçus ne sont rattachés"),
    ("audit.dividends.unlinked_description", "1 dividende n'est rattaché", "3 dividendes ne sont rattachés"),
    ("audit.unmatched_transfers.description", "1 virement interne potentiel", "3 virements internes potentiels"),
    ("audit.duplicates.description", "1 transaction semble", "3 transactions semblent"),
])
def test_plural_agrees_with_count(key: str, one: str, other: str):
    assert one in trn(key, 1, merchant="M", total=4)
    assert other in trn(key, 3, merchant="M", total=4)


def test_subscription_price_change_reads_in_french_amounts(monkeypatch, db_session):
    change = SimpleNamespace(
        name="Box", account_id=1, currency="EUR", frequency="monthly", old_amount=61.0, new_amount=96.0,
        changed_on=date(2026, 5, 3), delta_pct=57.4, annual_impact=420.0, key="k",
    )
    monkeypatch.setattr(subscription_prices, "detect_price_changes", lambda db: [change])
    (item,) = subscription_prices.detect(audit_context.AuditContext(db=db_session, now=datetime(2026, 6, 15)))
    assert "61,00\u00a0€ → 96,00\u00a0€" in item.description
    assert "420,00\u00a0€" in item.description and "+57,4 %" in item.description
    assert "EUR" not in item.description and "61.00" not in item.description


def test_budget_alert_amounts_in_french(monkeypatch, db_session):
    alert = SimpleNamespace(category_id=3, category_name="Courses", monthly_spent=120.5, monthly_limit=100.0, monthly_ratio=1.2)

    async def fake(**_):
        return [alert]

    monkeypatch.setattr(budget, "compute_budget_alerts", fake)
    (over,) = asyncio.run(budget.detect(audit_context.AuditContext(db=db_session, now=datetime(2026, 6, 15))))
    assert over.description == "Tu as dépensé 120,50\u00a0€ pour une limite de 100,00\u00a0€."
