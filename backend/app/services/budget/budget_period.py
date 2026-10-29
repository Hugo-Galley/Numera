"""Mois budgétaire : une période démarre à chaque salaire reçu.

Le salaire du 25 août finance septembre : la période « septembre » va du 25 août
(inclus) au salaire suivant (exclu). Les dates et les soldes des transactions ne
changent pas, seule la fenêtre de lecture des KPI mensuels bouge.

Sans salaire détecté (ou réglage `budget_month_mode = civil`), on retombe sur le mois
civil, ce qui laisse les calculs inchangés.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db.system_settings import get_setting, set_setting
from app.domain.budget_period import Period, bounds_in_periods, civil_bounds, distinct_salary_dates, periods_from_salary_dates
from app.repositories.budget.budget_period import salary_entry_dates

SETTING_KEY = "budget_month_mode"
MODE_CIVIL = "civil"
MODE_SALARY = "salary"
DEFAULT_MODE = MODE_SALARY


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


def salary_dates(db: Session) -> list[datetime]:
    """Dates (jour, sans heure) des salaires reçus, triées, sans doublon proche."""
    return distinct_salary_dates(salary_entry_dates(db))


def build_periods(db: Session) -> list[Period]:
    """Périodes de paie, de la plus ancienne à la plus récente (la dernière est ouverte)."""
    return periods_from_salary_dates(salary_dates(db), datetime.now())


def period_bounds(db: Session, year: int, month: int) -> tuple[datetime, datetime]:
    """Fenêtre [début, fin[ du mois budgétaire `year`/`month`."""
    if get_mode(db) == MODE_CIVIL:
        return civil_bounds(year, month)
    return bounds_in_periods(build_periods(db), year, month)


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


def period_info(db: Session, year: int | None = None, month: int | None = None) -> dict:
    """Mois budgétaire en cours et fenêtre (début / fin incluse) du mois demandé (par défaut, le mois en cours)."""
    current_year, current_month = current_period(db)
    info = describe(db, year or current_year, month or current_month)
    return {**info, "current": {"year": current_year, "month": current_month}}


def update_mode(db: Session, mode: str) -> dict:
    """Change le mode (civil ou mois de paie) et renvoie la période en cours."""
    set_mode(db, mode)
    return period_info(db)


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
    "MODE_CIVIL",
    "MODE_SALARY",
    "build_periods",
    "civil_months",
    "current_period",
    "describe",
    "get_mode",
    "months_back",
    "period_info",
    "period_bounds",
    "period_key_expr",
    "salary_dates",
    "set_mode",
    "update_mode",
]
