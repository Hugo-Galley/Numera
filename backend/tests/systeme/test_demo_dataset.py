"""Jeu de démo présentable : catégories accentuées et stylées, logos existants, salaire dans le mois qu'il finance."""
import asyncio
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.integrations import logos
from app.models.account import Account
from app.models.category import Category
from app.models.recurring_transaction import RecurringTransaction
from app.services.analytics.budget import compute_budget
from app.services.budget.budget_period import period_bounds
from app.services.systeme.demo import generate_demo_data

TODAY = date(2025, 3, 15)  # salaire le 27 : celui du 27 février finance mars


def _generate(db: Session) -> None:
    asyncio.run(generate_demo_data(db, today=TODAY))


def test_demo_categories_are_accented_and_styled(db_session: Session):
    _generate(db_session)
    categories = db_session.query(Category).all()
    names = {c.name for c in categories}

    assert {"Cadeaux (émis)", "Remboursement (reçu)", "Revenus supplémentaires"} <= names
    assert not names & {"Cadeaux (emis)", "Remboursement (recu)", "Revenus supplementaires", "Categorie"}
    assert [c.name for c in categories if not (c.color and c.icon)] == []


def test_demo_logos_all_exist_in_the_catalog(db_session: Session):
    _generate(db_session)
    refs = {r.logo for r in db_session.query(RecurringTransaction).all() if r.logo}
    refs |= {a.logo for a in db_session.query(Account).all() if getattr(a, "logo", None)}
    missing = [ref for ref in refs if ref.startswith("si:") and logos.simple_icon_svg(ref[3:]) is None]
    assert missing == []


def test_demo_salary_funds_the_following_month(db_session: Session):
    _generate(db_session)

    start, _ = period_bounds(db_session, 2025, 3)
    budget = asyncio.run(compute_budget(db_session, month=3, year=2025))

    assert start == datetime(2025, 2, 27)
    assert budget["revenus_totaux"] > 0
