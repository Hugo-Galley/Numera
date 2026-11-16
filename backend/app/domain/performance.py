"""Mesures de performance d'un portefeuille : rendement annualisé (XIRR), pondéré par le temps (TWR), pire baisse."""
from datetime import date as date_type
from typing import Any

from app.domain.holdings import EPSILON


def xirr(flows: list[tuple[date_type, float]]) -> float | None:
    """Taux de rendement annualisé pondéré par les montants (flux < 0 : argent investi, > 0 : récupéré).

    Renvoie None s'il n'y a pas à la fois un flux positif et un flux négatif, ou pas de solution.
    """
    flows = [(d, a) for d, a in flows if a]
    if len(flows) < 2 or not any(a > 0 for _, a in flows) or not any(a < 0 for _, a in flows):
        return None
    origin = min(d for d, _ in flows)
    spans = [((d - origin).days / 365.0, a) for d, a in flows]

    def npv(rate: float) -> float:
        return float(sum(a / (1.0 + rate) ** t for t, a in spans))

    low, high = -0.9999, 1000.0
    f_low, f_high = npv(low), npv(high)
    if f_low * f_high > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-9:
            return mid
        if f_low * f_mid < 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2.0


def twr(points: list[tuple[date_type, float, float]]) -> float | None:
    """Performance pondérée par le temps, indépendante du moment des versements.

    `points` : (jour, valeur en fin de journée, flux externe net du jour : versement − retrait), triés.
    Entre deux points, rendement = (valeur avant le flux du jour) / (valeur du point précédent).
    """
    if len(points) < 2:
        return None
    return performance_index(points)[-1][1] - 1.0


def performance_index(points: list[tuple[date_type, float, float]]) -> list[tuple[date_type, float]]:
    """Indice de performance cumulée neutre des flux (base 1 au premier point), chaîné comme `twr`."""
    if not points:
        return []
    index = [(points[0][0], 1.0)]
    level = 1.0
    previous = points[0][1]
    for day, value, flow in points[1:]:
        if previous > EPSILON:
            level *= (value - flow) / previous
        index.append((day, level))
        previous = value
    return index


def max_drawdown(points: list[tuple[date_type, float, float]]) -> dict[str, Any] | None:
    """Pire baisse d'un sommet à un creux, mesurée sur l'indice neutre des flux (un versement ne la masque pas).

    `points` : comme `twr`. Renvoie la baisse en % (≤ 0), les dates du sommet, du creux et du retour au sommet
    (None = pas encore récupéré) et la baisse actuelle sous le plus haut. None s'il y a moins de deux points.
    """
    index = performance_index(points)
    if len(index) < 2:
        return None
    peak_day, peak = index[0]
    worst = 0.0
    worst_peak_day: date_type | None = None
    trough_day: date_type | None = None
    worst_peak = peak
    for day, level in index[1:]:
        if level > peak:
            peak_day, peak = day, level
        elif peak > EPSILON and level / peak - 1.0 < worst:
            worst, worst_peak_day, trough_day, worst_peak = level / peak - 1.0, peak_day, day, peak
    recovery_day = None
    if trough_day is not None:
        recovery_day = next((day for day, level in index if day > trough_day and level >= worst_peak - EPSILON), None)
    last_level = index[-1][1]
    current = last_level / peak - 1.0 if peak > EPSILON else 0.0
    return {
        "max_drawdown_pct": round(worst * 100.0, 2),
        "peak_date": worst_peak_day,
        "trough_date": trough_day,
        "recovery_date": recovery_day,
        "current_drawdown_pct": round(min(current, 0.0) * 100.0, 2),
    }


def combine_points(series: list[list[tuple[date_type, float, float]]]) -> list[tuple[date_type, float, float]]:
    """Points (jour, valeur, flux) de plusieurs comptes réunis sur l'union de leurs jours.

    Un compte sans point ce jour-là garde sa dernière valeur (aucun flux) ; son premier point entre comme
    un versement de toute sa valeur, pour qu'un compte ouvert plus tard ne passe pas pour une hausse.
    """
    days = sorted({day for points in series for day, _, _ in points})
    by_day = [{day: (value, flow) for day, value, flow in points} for points in series]
    last: list[float | None] = [None] * len(series)
    combined: list[tuple[date_type, float, float]] = []
    for index, day in enumerate(days):
        total = flow_total = 0.0
        for i, points in enumerate(by_day):
            if day in points:
                value, flow = points[day]
                flow_total += value if last[i] is None and index > 0 else flow
                last[i] = value
            total += last[i] or 0.0
        combined.append((day, total, flow_total))
    return combined
