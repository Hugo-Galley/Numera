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
    """Rendement moyen pondéré, sur les semaines où toutes les séries retenues ont une valeur.

    Une série sous `MIN_HISTORY_WEEKS` (fonds acheté récemment) est laissée de côté dès qu'une autre a assez
    d'historique : elle réduirait sinon tout le panier à ses quelques semaines."""
    used = {key: w for key, w in weights.items() if w > 0 and key in series}
    if not used:
        return {}
    long_enough = {key: w for key, w in used.items() if len(series[key]) >= MIN_HISTORY_WEEKS}
    used = long_enough or used
    total = sum(used.values())
    weeks = set.intersection(*(set(series[key]) for key in used))
    return {week: sum(series[key][week] * w for key, w in used.items()) / total for week in sorted(weeks)}


def overlap(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    """Recouvrement de deux répartitions, chacune ramenée à 1 : Σ min(aᵢ, bᵢ) = 1 − active share ; 0.0 si l'une est
    vide. Contrairement au cosinus, une composante dominante commune (l'USA d'un S&P 500 et d'un World) ne suffit pas."""
    total_a = sum(v for v in a.values() if v > 0)
    total_b = sum(v for v in b.values() if v > 0)
    if total_a <= 0 or total_b <= 0:
        return 0.0
    return sum(min(max(a[k], 0.0) / total_a, max(b[k], 0.0) / total_b) for k in a.keys() & b.keys())
