"""Requêtes du mois budgétaire : dates des salaires reçus."""
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.salary_config import SalaryConfig
from app.models.transaction import Transaction


def salary_entry_dates(db: Session) -> set[datetime]:
    """Dates (jour, sans heure) des salaires reçus sur les comptes de salaire actifs."""
    configs = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).all()  # noqa: E712
    if not configs:
        return set()

    rows: set[datetime] = set()
    for config in configs:
        criteria = [func.lower(Transaction.merchant).like("salaire%")]
        if config.salary_recurring_id:
            criteria.append(Transaction.recurring_transaction_id == config.salary_recurring_id)
        if config.salary_category_id:
            criteria.append(Transaction.category_id == config.salary_category_id)
        # Salaires importés de la banque : libellé de l'employeur, mais catégorie « Salaire ».
        criteria.append(
            Transaction.category_id.in_(db.query(Category.id).filter(func.lower(Category.name) == "salaire"))
        )
        query = db.query(Transaction.date).filter(
            Transaction.account_id == config.salary_account_id,
            Transaction.type == "Entree",
            Transaction.is_transfer == False,  # noqa: E712
            or_(*criteria),
        )
        rows.update(datetime(d.year, d.month, d.day) for (d,) in query.all())

    return rows
