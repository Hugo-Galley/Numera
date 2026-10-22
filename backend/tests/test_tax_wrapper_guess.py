import pytest

from app.core.tax import guess_tax_wrapper
from app.models.account import Account


@pytest.mark.parametrize("name, account_type, expected", [
    ("PEA", "investissement", "pea"),
    ("PEA-PME Boursorama", "investissement", "pea"),
    ("PEEG", "investissement", "pee"),
    ("PER Axa", "investissement", "per"),
    ("PERCO", "investissement", "per"),
    ("Compte Titres", "investissement", "cto"),
    ("CTO Trade Republic", "investissement", "cto"),
    ("Assurance-Vie BRED", "investissement", "assurance_vie"),
    ("Linxea", "assurance_vie", "assurance_vie"),
    ("Livret A", "epargne", "livret_a"),
    ("Livret Jeune", "epargne", "livret_jeune"),
    ("Ledger", "investissement", None),
    ("Principale", "courant", None),
    ("Péage autoroute", "courant", None),
])
def test_guess_tax_wrapper(name, account_type, expected):
    assert guess_tax_wrapper(name, account_type) == expected


def test_overview_suggests_a_wrapper_for_accounts_without_one(client, db_session):
    """Le PEA n'avait pas d'enveloppe : absent de la page Fiscalité sans que rien ne le signale."""
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    livret = Account(name="Livret A", type="epargne", currency="EUR", active=True, tax_wrapper="livret_a")
    closed = Account(name="PEA ancien", type="investissement", currency="EUR", active=False)
    db_session.add_all([pea, livret, closed])
    db_session.commit()

    suggestions = client.get("/tax/overview").json()["suggestions"]
    assert suggestions == [{"account_id": pea.id, "account_name": "PEA", "kind": "pea"}]
