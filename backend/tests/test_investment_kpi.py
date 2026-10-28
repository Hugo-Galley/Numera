from datetime import datetime

from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction

DAY = datetime(2025, 10, 10)


def _setup(db):
    courant = Account(name="Principal", type="courant", currency="EUR", active=True)
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    invest = Category(name="Investissement", type="depense")
    db.add_all([courant, pea, invest])
    db.commit()
    return courant, pea, invest


def _tx(db, acc, type_, amount, merchant, category=None, **extra):
    t = Transaction(
        account_id=acc.id, date=DAY, month_label=month_label_from_date(DAY), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR",
        running_balance=0.0, category_id=category.id if category else None, **extra,
    )
    db.add(t)
    db.commit()
    return t


def _versement(db, acc, amount, note):
    v = InvestmentTransaction(
        account_id=acc.id, date=DAY, type="versement", amount=amount,
        original_amount=amount, currency="EUR", note=note,
    )
    db.add(v)
    db.commit()
    return v


def _budget(client):
    return client.get("/analytics/budget", params={"month": 10, "year": 2025}).json()


def test_external_versement_is_not_budget_investment(client, db_session):
    courant, pea, invest = _setup(db_session)
    _tx(db_session, courant, "Entree", 2000.0, "SALAIRE")
    _tx(db_session, courant, "Sortie", 300.0, "MARCHE")
    _tx(db_session, courant, "Sortie", 400.0, "Alimentation PEA", invest)
    _versement(db_session, pea, 5000.0, "Rapatriement ancienne assurance vie")

    data = _budget(client)

    assert data["investissements_du_mois"] == 400.0
    assert data["depenses_reelles"] == 300.0


def test_linked_versement_counts_once_and_is_not_deducted_from_expenses(client, db_session):
    courant, pea, invest = _setup(db_session)
    _tx(db_session, courant, "Entree", 2000.0, "SALAIRE")
    _tx(db_session, courant, "Sortie", 300.0, "MARCHE")
    versement = _versement(db_session, pea, 250.0, "Alimentation PEA")
    _tx(
        db_session, courant, "Sortie", 250.0, "Alimentation PEA", invest,
        is_transfer=True, linked_investment_transaction_id=versement.id,
    )

    data = _budget(client)

    assert data["investissements_du_mois"] == 250.0
    assert data["depenses_reelles"] == 300.0
    assert data["depenses_totales"] == 300.0
