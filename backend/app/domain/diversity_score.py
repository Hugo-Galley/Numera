"""Score de diversification (indice de Herfindahl-Hirschman) et son libellé."""

from __future__ import annotations

from app.core.i18n import tr


def hhi_score(weights: list[float]) -> float:
    """
    Computes a 0-100 score based on Herfindahl-Hirschman Index (HHI).
    HHI ranges from ~0 (infinite diversity) to 10,000 (100% single asset).
    Score:
      HHI <= 1000 -> 90 - 100
      HHI 1000 - 1800 -> 75 - 89
      HHI 1800 - 2500 -> 55 - 74
      HHI > 2500 -> 10 - 54
    """
    if not weights or sum(weights) <= 0:
        return 50.0

    total = sum(weights)
    hhi = sum(((w / total) * 100.0) ** 2 for w in weights)

    # Invert HHI to a 0-100 score
    if hhi <= 1000:
        score = 90.0 + (1000.0 - hhi) / 1000.0 * 10.0
    elif hhi <= 1800:
        score = 75.0 + (1800.0 - hhi) / 800.0 * 15.0
    elif hhi <= 2500:
        score = 55.0 + (2500.0 - hhi) / 700.0 * 20.0
    elif hhi <= 5000:
        score = 30.0 + (5000.0 - hhi) / 2500.0 * 25.0
    else:
        score = max(10.0, 30.0 * (10000.0 - hhi) / 5000.0)

    return round(min(100.0, max(5.0, score)), 1)


def score_label(score: float) -> str:
    if score < 40:
        return tr("diversity.score_critical")
    if score < 60:
        return tr("diversity.score_moderate")
    if score < 80:
        return tr("diversity.score_good")
    return tr("diversity.score_excellent")
