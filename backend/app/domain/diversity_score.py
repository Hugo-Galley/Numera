"""Libellé du score de diversification (le score, écart à la référence de marché, vient de `domain/exposure/`)."""

from __future__ import annotations

from app.core.i18n import tr


def score_label(score: float) -> str:
    if score < 40:
        return tr("diversity.score_critical")
    if score < 60:
        return tr("diversity.score_moderate")
    if score < 80:
        return tr("diversity.score_good")
    return tr("diversity.score_excellent")
