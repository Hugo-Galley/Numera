"""Écarts au marché par dimension (pays, secteurs, sociétés) et score de diversification relatif.

Calcul pur (spec 2026-11-27, § 4 et § 5). Les deux côtés sont des montants ou des pourcentages quelconques : les
libellés sans information (« Non renseigné », « Autres », liquidités) sont retirés des deux côtés, puis chaque côté
est renormalisé à 100 sur sa part connue."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.domain.diversity import CASH_LABEL
from app.domain.etf_normalize import UNKNOWN_LABEL
from app.domain.exposure.params import OVERWEIGHT_MIN_POINTS, OVERWEIGHT_RATIO

EXCLUDED_LABELS = frozenset({UNKNOWN_LABEL, CASH_LABEL, "Autres"})
# Sans dimension comparable (pas de référence de marché), le score est neutre
NEUTRAL_SCORE = 50.0


@dataclass(frozen=True)
class GapRow:
    name: str
    portfolio_pct: float
    market_pct: float
    # Le nom est absent d'un marché connu partiellement (top holdings) : market_pct est un majorant
    market_pct_is_upper_bound: bool
    gap_pts: float


@dataclass(frozen=True)
class DimensionGap:
    active_share_pct: float
    # Part du portefeuille réellement décrite et comparée (hors libellés sans information)
    covered_pct: float
    rows: tuple[GapRow, ...]
    # Faux si l'un des deux côtés n'a rien de comparable (composition inconnue, référence sans pays ni secteurs) :
    # la dimension n'entre ni dans le score ni dans les alertes
    comparable: bool = True


def _known(weights: Mapping[str, float]) -> dict[str, float]:
    return {name: w for name, w in weights.items() if name not in EXCLUDED_LABELS and w > 0}


def _normalized(weights: Mapping[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {name: w * 100 / total for name, w in weights.items()} if total > 0 else {}


def _active_share(w: Mapping[str, float], b: Mapping[str, float], undescribed: float) -> float:
    """½ (Σ |w − b| sur les noms décrits du portefeuille + la part du marché hors de ces noms que la part non
    décrite du portefeuille ne peut pas porter). Portefeuille entièrement décrit : ½ Σ |w − b| classique."""
    described = sum(abs(w[name] - b.get(name, 0.0)) for name in w)
    elsewhere = sum(weight for name, weight in b.items() if name not in w)
    return (described + max(0.0, elsewhere - undescribed)) / 2


def dimension_gap(
    portfolio: Mapping[str, float],
    market: Mapping[str, float],
    market_floor: float | None = None,
    renormalize: bool = True,
) -> DimensionGap:
    """Écart du portefeuille au marché sur une dimension.

    `renormalize` (pays, secteurs) : les deux côtés, montants ou % quelconques, sont ramenés à 100 sur leur part
    connue. Sans renormalisation (sociétés) : `portfolio` est déjà en % de la valeur boursière totale et `market`
    en poids publiés bruts ; la part non décrite du portefeuille n'est pas inventée. `market_floor` (marché
    partiel) : poids majorant d'un nom absent du marché, dans les unités de `market`, pour l'affichage et la
    sur-pondération seulement."""
    known = _known(portfolio)
    market_known = _known(market)
    if renormalize:
        portfolio_total = sum(portfolio.values())
        covered = sum(known.values()) * 100 / portfolio_total if portfolio_total > 0 else 0.0
        w, b = _normalized(known), _normalized(market_known)
        market_total = sum(market_known.values())
        floor = market_floor * 100 / market_total if market_floor is not None and market_total > 0 else None
    else:
        covered = min(100.0, sum(known.values()))
        w, b, floor = dict(known), market_known, market_floor
    if not w or not b:
        return DimensionGap(active_share_pct=0.0, covered_pct=covered if w else 0.0, rows=(), comparable=False)

    undescribed = max(0.0, 100.0 - sum(w.values()))
    # Un nom du marché absent d'un portefeuille partiellement décrit n'est pas « à 0 % » : on ne le liste pas
    names = w.keys() | b.keys() if undescribed <= 0.5 else set(w)
    rows: list[GapRow] = []
    for name in names:
        mine = w.get(name, 0.0)
        bound = name not in b and floor is not None
        theirs = b.get(name, floor or 0.0)
        rows.append(GapRow(name, mine, theirs, bound, mine - theirs))
    rows.sort(key=lambda r: (-r.gap_pts, r.name))
    return DimensionGap(active_share_pct=_active_share(w, b, undescribed), covered_pct=covered, rows=tuple(rows))


def is_overweight(row: GapRow) -> bool:
    return row.portfolio_pct >= OVERWEIGHT_RATIO * row.market_pct and row.gap_pts >= OVERWEIGHT_MIN_POINTS


def market_score(gaps: Sequence[DimensionGap]) -> float:
    """100 − moyenne des active shares des dimensions comparables, borné à [0, 100] ; neutre sans dimension
    comparable (une dimension dont rien n'est connu n'est pas « identique au marché »)."""
    comparable = [g for g in gaps if g.comparable and g.covered_pct > 0]
    if not comparable:
        return NEUTRAL_SCORE
    mean = sum(g.active_share_pct for g in comparable) / len(comparable)
    return round(min(100.0, max(0.0, 100.0 - mean)), 1)
