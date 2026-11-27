"""Statistiques pures du modèle de sur-exposition : rendements hebdomadaires, corrélation, tracking error, cosinus.

Bibliothèque standard seulement. Les séries de rendements sont indexées par le vendredi ISO de leur semaine."""

import math
import statistics
from collections.abc import Mapping, Sequence
from datetime import date, timedelta

from app.domain.exposure.params import MIN_HISTORY_WEEKS

WEEKS_PER_YEAR = 52


def _iso_friday(day: date) -> date:
    year, week, _ = day.isocalendar()
    return date.fromisocalendar(year, week, 5)


def weekly_returns(series: Sequence[tuple[date, float]]) -> dict[date, float]:
    """Rendement simple de chaque semaine ISO depuis la précédente, sur la dernière clôture de chaque semaine.

    Une semaine dont la semaine ISO précédente n'a aucune clôture n'a pas de rendement."""
    closes: dict[date, float] = {}
    for day, close in sorted(series, key=lambda point: point[0]):
        closes[_iso_friday(day)] = close
    returns: dict[date, float] = {}
    for friday, close in closes.items():
        previous = closes.get(friday - timedelta(weeks=1))
        if previous:
            returns[friday] = close / previous - 1
    return returns


def _common(a: Mapping[date, float], b: Mapping[date, float]) -> tuple[list[float], list[float]]:
    keys = sorted(a.keys() & b.keys())
    return [a[k] for k in keys], [b[k] for k in keys]


def correlation(a: Mapping[date, float], b: Mapping[date, float]) -> float | None:
    """Corrélation de Pearson sur les semaines communes ; None sous MIN_HISTORY_WEEKS ou si une variance est nulle."""
    xs, ys = _common(a, b)
    if len(xs) < MIN_HISTORY_WEEKS:
        return None
    try:
        return statistics.correlation(xs, ys)
    except statistics.StatisticsError:
        return None


def tracking_error(a: Mapping[date, float], b: Mapping[date, float]) -> float | None:
    """Écart-type (échantillon) des écarts de rendements hebdomadaires, annualisé ; None sous MIN_HISTORY_WEEKS."""
    xs, ys = _common(a, b)
    if len(xs) < MIN_HISTORY_WEEKS:
        return None
    return statistics.stdev(x - y for x, y in zip(xs, ys, strict=True)) * math.sqrt(WEEKS_PER_YEAR)


def cosine(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    """Similarité cosinus de deux vecteurs creux ; 0.0 si l'un est vide ou nul."""
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    if norm == 0:
        return 0.0
    return sum(v * b[k] for k, v in a.items() if k in b) / norm


def weighted_returns(series: Mapping[str, Mapping[date, float]], weights: Mapping[str, float]) -> dict[date, float]:
    """Rendement moyen pondéré, sur les semaines où toutes les séries de poids non nul ont une valeur."""
    used = {key: w for key, w in weights.items() if w > 0 and key in series}
    if not used:
        return {}
    total = sum(used.values())
    weeks = set.intersection(*(set(series[key]) for key in used))
    return {week: sum(series[key][week] * w for key, w in used.items()) / total for week in sorted(weeks)}
