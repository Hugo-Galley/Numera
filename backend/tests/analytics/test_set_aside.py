"""Deux notions distinctes : solde du mois (revenus − dépenses réelles) et mis de côté (argent envoyé vers l'épargne)."""
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


def _account(db: Session, name: str, type_: str) -> Account:
    acc = Account(name=name, type=type_, currency="EUR", active=True)
    db.add(acc)
    db.commit()
    return acc


def _tx(db: Session, acc: Account, type_: str, amount: float, day: datetime, merchant: str, **extra: object) -> Transaction:
    t = Transaction(account_id=acc.id, date=day, month_label="x", type=type_, merchant=merchant, amount=amount,
                    original_amount=amount, currency="EUR", running_balance=0.0, **extra)
    db.add(t)
    db.commit()
    return t


def _transfer(db: Session, src: Account, dst: Account, amount: float, day: datetime) -> None:
    out = _tx(db, src, "Sortie", amount, day, f"VIR {dst.name}", is_transfer=True)
    inc = _tx(db, dst, "Entree", amount, day, f"VIR {src.name}", is_transfer=True, linked_transaction_id=out.id)
    out.linked_transaction_id = inc.id
    db.commit()


def _setup(db: Session) -> None:
    courant = _account(db, "Courant", "courant")
    livret = _account(db, "Livret A", "epargne")
    av = _account(db, "Assurance-vie", "assurance_vie")
    epargne = Category(name="Epargne", type="depense")
    db.add(epargne)
    db.commit()
    day = datetime(2026, 5, 3, 12)
    _tx(db, courant, "Entree", 2000.0, day, "SALAIRE")
    _tx(db, courant, "Sortie", 1200.0, day + timedelta(days=1), "COURSES")
    _tx(db, courant, "Sortie", 50.0, day + timedelta(days=2), "CAGNOTTE", category_id=epargne.id)
    _transfer(db, courant, livret, 200.0, day)
    _transfer(db, courant, av, 100.0, day)
    _transfer(db, livret, courant, 80.0, day + timedelta(days=5))  # retour d'épargne : retranché


def test_budget_exposes_solde_du_mois_and_mis_de_cote(client: TestClient, db_session: Session):
    _setup(db_session)

    data = client.get("/analytics/budget", params={"month": 5, "year": 2026}).json()

    assert data["solde_du_mois"] == data["epargne_realisee"] == 2000.0 - 1200.0
    # 50 (sortie catégorisée Épargne) + 200 (Livret A) + 100 (assurance-vie) − 80 (retour vers le courant)
    assert data["investissements_du_mois"] == 50.0
    assert data["mis_de_cote"] == 270.0


def test_monthly_report_set_aside_is_the_budget_figure(client: TestClient, db_session: Session):
    _setup(db_session)

    report = client.get("/analytics/monthly-report", params={"month": 5, "year": 2026}).json()

    assert report["set_aside"] == 270.0
    assert report["savings"] == 800.0
