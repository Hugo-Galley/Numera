"""Mesures de performance d'un portefeuille : rendement annualisé (XIRR) et pondéré par le temps (TWR)."""
from datetime import date as date_type

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
        return sum(a / (1.0 + rate) ** t for t, a in spans)

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
    factor = 1.0
    previous = points[0][1]
    for _, value, flow in points[1:]:
        if previous > EPSILON:
            factor *= (value - flow) / previous
        previous = value
    return factor - 1.0
