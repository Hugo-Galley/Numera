"""Hausse de prix d'une série de prélèvements réguliers (calcul pur, sans base).

Une série est retenue si ses échéances sont régulières (mensuelle, trimestrielle ou annuelle) ;
une hausse est signalée quand le dernier prélèvement dépasse un montant précédent stable.
"""
from dataclasses import dataclass
from datetime import date, datetime
from itertools import pairwise
from statistics import median
from typing import Any, Sequence

# (écart médian min, max en jours, prélèvements par an, libellé)
CADENCES = (
    (25, 35, 12, "monthly"),
    (80, 100, 4, "quarterly"),
    (340, 390, 1, "yearly"),
)
LOOKBACK_DAYS = 800  # deux ans et plus : une hausse annuelle a besoin de l'échéance précédente
MIN_INCREASE = 0.10  # en devise du compte, sous ce seuil c'est un arrondi
MIN_INCREASE_PCT = 0.01
EPS = 0.005
# Une hausse reste signalée ~6 mois (un an pour un prélèvement annuel), puis devient le prix normal
RECENT_DAYS = 180


@dataclass
class PriceChange:
    key: str
    name: str
    account_id: int
    currency: str
    frequency: str
    old_amount: float
    new_amount: float
    changed_on: date
    per_year: int

    @property
    def delta(self) -> float:
        return round(self.new_amount - self.old_amount, 2)

    @property
    def delta_pct(self) -> float:
        return round(self.delta / self.old_amount * 100, 1) if self.old_amount else 0.0

    @property
    def annual_impact(self) -> float:
        return round(self.delta * self.per_year, 2)


def price_change_id(change: PriceChange) -> str:
    return f"subscription-price-{change.account_id}-{change.key}-{change.changed_on.isoformat()}"


def _cadence(dates: list[datetime]) -> tuple[int, str] | None:
    gaps = [(b - a).days for a, b in pairwise(dates)]
    if not gaps:
        return None
    gap = median(gaps)
    for low, high, per_year, label in CADENCES:
        if low <= gap <= high:
            return per_year, label
    return None


@dataclass
class SeriesChange:
    old_amount: float
    new_amount: float
    changed_on: date
    per_year: int
    frequency: str


def series_change(rows: Sequence[Any], now: datetime) -> SeriesChange | None:
    """Hausse récente d'une série triée par date (lignes avec `date` et `amount`), sinon None."""
    if len(rows) < 2:
        return None
    cadence = _cadence([r.date for r in rows])
    if cadence is None:
        return None
    per_year, frequency = cadence
    last = rows[-1]
    # Dernier prélèvement récent : une série arrêtée n'est plus un abonnement en cours
    if (now - last.date).days > 1.5 * 365 / per_year:
        return None
    # Nouveau tarif = dernière suite de montants identiques ; ancien = suite stable juste avant
    new = float(last.amount)
    start = len(rows) - 1
    while start > 0 and abs(float(rows[start - 1].amount) - new) <= EPS:
        start -= 1
    changed = rows[start]
    if (now - changed.date).days > max(RECENT_DAYS, 1.1 * 365 / per_year):
        return None
    needed = 1 if per_year == 1 else 2  # l'annuel n'a souvent qu'une échéance précédente
    reference = [float(r.amount) for r in rows[max(0, start - needed):start]]
    if len(reference) < needed:
        return None
    old = reference[-1]
    if any(abs(a - old) > EPS for a in reference):
        return None
    if new - old < MIN_INCREASE or new < old * (1 + MIN_INCREASE_PCT):
        return None
    return SeriesChange(round(old, 2), round(new, 2), changed.date.date(), per_year, frequency)
