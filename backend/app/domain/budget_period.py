"""Mois budgétaire : calcul pur des périodes de paie à partir des dates de salaire.

Le salaire du 25 août finance septembre : la période « septembre » va du 25 août
(inclus) au salaire suivant (exclu). Sans salaire, mois civil.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta

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


def distinct_salary_dates(rows: set[datetime]) -> list[datetime]:
    """Dates de salaire triées, sans les doublons proches (prime, régularisation)."""
    dates: list[datetime] = []
    for d in sorted(rows):
        if dates and (d - dates[-1]).days < MIN_PERIOD_DAYS:
            continue
        dates.append(d)
    return dates


def periods_from_salary_dates(starts: list[datetime], now: datetime) -> list[Period]:
    """Périodes de paie, de la plus ancienne à la plus récente (la dernière est ouverte)."""
    periods: list[Period] = []
    for index, start in enumerate(starts):
        if index + 1 < len(starts):
            end = starts[index + 1]
            if (end - start).days > OPEN_PERIOD_MAX_DAYS:
                # Salaire manquant : la période ne s'étire pas sur deux mois.
                end = _add_month(start)
        else:
            end = _add_month(start)
            tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            if end < tomorrow <= start + timedelta(days=OPEN_PERIOD_MAX_DAYS):
                end = tomorrow
        year, month = _label_for(start)
        # Deux salaires qui financent le même mois : on garde le premier, qui absorbe la fenêtre du second.
        if periods and (periods[-1].year, periods[-1].month) == (year, month):
            last = periods[-1]
            periods[-1] = Period(last.year, last.month, last.start, end)
            continue
        periods.append(Period(year, month, start, end))
    return _fill_gaps(periods)


def _fill_gaps(periods: list[Period]) -> list[Period]:
    """Comble les trous entre deux périodes de paie (salaire manquant) par des mois sans salaire.

    Chaque jour appartient ainsi à exactement une période : sans cela, les dépenses d'un mois
    sans salaire disparaissaient des KPI (audit A1).
    """
    filled: list[Period] = []
    for index, period in enumerate(periods):
        filled.append(period)
        if index + 1 >= len(periods):
            break
        following = periods[index + 1]
        cursor = period.end
        year, month = period.year, period.month
        while cursor < following.start:
            month += 1
            if month > 12:
                year, month = year + 1, 1
            if (year, month) >= (following.year, following.month):
                # Plus de mois libre avant la période suivante : le dernier mois absorbe le reste
                filled[-1] = Period(filled[-1].year, filled[-1].month, filled[-1].start, following.start)
                break
            end = _add_month(cursor)
            if (following.start - end).days < MIN_PERIOD_DAYS:
                end = following.start  # reste trop court pour un mois à lui seul
            filled.append(Period(year, month, cursor, end))
            cursor = end
    return filled


def bounds_in_periods(periods: list[Period], year: int, month: int) -> tuple[datetime, datetime]:
    """Fenêtre [début, fin[ du mois `year`/`month` parmi les périodes de paie (repli : mois civil rogné)."""
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
