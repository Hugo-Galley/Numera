"""Mois budgétaire : une période démarre à chaque salaire reçu.

Le salaire du 25 août finance septembre : la période « septembre » va du 25 août
(inclus) au salaire suivant (exclu). Les dates et les soldes des transactions ne
changent pas, seule la fenêtre de lecture des KPI mensuels bouge.

Sans salaire détecté (ou réglage `budget_month_mode = civil`), on retombe sur le mois
civil, ce qui laisse les calculs inchangés.
"""
from __future__ import annotations

import calendar
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.db.system_settings import get_setting, set_setting
from app.models.category import Category
from app.models.salary_config import SalaryConfig
from app.models.transaction import Transaction

SETTING_KEY = "budget_month_mode"
MODE_CIVIL = "civil"
MODE_SALARY = "salary"
DEFAULT_MODE = MODE_SALARY

# Deux « salaires » à moins de ce délai (prime, régularisation) ne coupent pas la période.
MIN_PERIOD_DAYS = 15
# Salaire en retard : la dernière période reste ouverte jusqu'à ce délai après son début.
OPEN_PERIOD_MAX_DAYS = 45
# Un salaire reçu après ce lendemain de début de mois finance le mois suivant.
LABEL_OFFSET_DAYS = 15


@dataclass(frozen=True)
class Period:
    year: int
    month: int
    start: datetime
    end: datetime  # exclu

    @property
    def key(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


_force_civil: ContextVar[bool] = ContextVar("budget_period_force_civil", default=False)


@contextmanager
def civil_months():
    """Force le mois civil le temps d'un calcul (bilan annuel, hors mois de paie)."""
    token = _force_civil.set(True)
    try:
        yield
    finally:
        _force_civil.reset(token)


def get_mode(db: Session) -> str:
    if _force_civil.get():
        return MODE_CIVIL
    value = str(get_setting(db, SETTING_KEY, DEFAULT_MODE)).lower()
    return value if value in (MODE_CIVIL, MODE_SALARY) else DEFAULT_MODE


def set_mode(db: Session, mode: str) -> str:
    if mode not in (MODE_CIVIL, MODE_SALARY):
        raise ValueError("mode invalide")
    set_setting(db, SETTING_KEY, mode)
    return mode


def civil_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    return start, end


def _add_month(d: datetime) -> datetime:
    year = d.year + (1 if d.month == 12 else 0)
    month = 1 if d.month == 12 else d.month + 1
    return d.replace(year=year, month=month, day=min(d.day, calendar.monthrange(year, month)[1]))


def _label_for(start: datetime) -> tuple[int, int]:
    """Mois financé par un salaire reçu à `start`."""
    ref = start + timedelta(days=LABEL_OFFSET_DAYS)
    return ref.year, ref.month


def salary_dates(db: Session) -> list[datetime]:
    """Dates (jour, sans heure) des salaires reçus, triées, sans doublon proche."""
    configs = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).all()  # noqa: E712
    if not configs:
        return []

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

    dates: list[datetime] = []
    for d in sorted(rows):
        if dates and (d - dates[-1]).days < MIN_PERIOD_DAYS:
            continue
        dates.append(d)
    return dates


def build_periods(db: Session) -> list[Period]:
    """Périodes de paie, de la plus ancienne à la plus récente (la dernière est ouverte)."""
    starts = salary_dates(db)
    periods: list[Period] = []
    for index, start in enumerate(starts):
        if index + 1 < len(starts):
            end = starts[index + 1]
            if (end - start).days > OPEN_PERIOD_MAX_DAYS:
                # Salaire manquant : la période ne s'étire pas sur deux mois.
                end = _add_month(start)
        else:
            end = _add_month(start)
            tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            if end < tomorrow <= start + timedelta(days=OPEN_PERIOD_MAX_DAYS):
                end = tomorrow
        year, month = _label_for(start)
        # Deux salaires qui financent le même mois : on garde le premier.
        if periods and (periods[-1].year, periods[-1].month) == (year, month):
            continue
        periods.append(Period(year, month, start, end))
    return periods


def period_bounds(db: Session, year: int, month: int) -> tuple[datetime, datetime]:
    """Fenêtre [début, fin[ du mois budgétaire `year`/`month`."""
    if get_mode(db) == MODE_CIVIL:
        return civil_bounds(year, month)
    periods = build_periods(db)
    for period in periods:
        if (period.year, period.month) == (year, month):
            return period.start, period.end
    start, end = civil_bounds(year, month)
    # Mois sans salaire : on ne chevauche jamais une période de paie voisine.
    for period in periods:
        if period.start <= start < period.end:
            start = period.end
        if start < period.start < end:
            end = period.start
    return start, max(start, end)


def current_period(db: Session, today: datetime | None = None) -> tuple[int, int]:
    """Mois budgétaire en cours (celui dont la fenêtre contient aujourd'hui)."""
    today = today or datetime.now()
    if get_mode(db) == MODE_SALARY:
        for period in reversed(build_periods(db)):
            if period.start <= today < period.end:
                return period.year, period.month
    return today.year, today.month


def period_key_expr(db: Session, column, first: datetime, last: datetime):
    """Expression SQL « AAAA-MM » du mois budgétaire d'une date (remplace strftime)."""
    if get_mode(db) == MODE_CIVIL:
        return func.strftime("%Y-%m", column)
    periods = [p for p in build_periods(db) if p.end > first and p.start < last]
    if not periods:
        return func.strftime("%Y-%m", column)
    whens = [((column >= p.start) & (column < p.end), p.key) for p in periods]
    return case(*whens, else_=func.strftime("%Y-%m", column))


def months_back(db: Session, count: int, today: datetime | None = None) -> list[tuple[int, int]]:
    """`count` mois budgétaires se terminant au mois en cours, du plus ancien au plus récent."""
    year, month = current_period(db, today)
    base = year * 12 + (month - 1)
    return [((base - i) // 12, (base - i) % 12 + 1) for i in range(count - 1, -1, -1)]


def describe(db: Session, year: int, month: int) -> dict:
    start, end = period_bounds(db, year, month)
    return {
        "year": year,
        "month": month,
        "mode": get_mode(db),
        "start": start.date().isoformat(),
        "end": (end - timedelta(days=1)).date().isoformat(),
    }


__all__ = [
    "Period",
    "MODE_CIVIL",
    "MODE_SALARY",
    "build_periods",
    "civil_bounds",
    "civil_months",
    "current_period",
    "describe",
    "get_mode",
    "months_back",
    "period_bounds",
    "period_key_expr",
    "salary_dates",
    "set_mode",
]
