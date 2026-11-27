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
    # Part du portefeuille conservée après exclusion des libellés sans information
    covered_pct: float
    rows: tuple[GapRow, ...]


def _known(weights: Mapping[str, float]) -> dict[str, float]:
    return {name: w for name, w in weights.items() if name not in EXCLUDED_LABELS and w > 0}


def _normalized(weights: Mapping[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {name: w * 100 / total for name, w in weights.items()} if total > 0 else {}


def dimension_gap(
    portfolio: Mapping[str, float],
    market: Mapping[str, float],
    market_floor: float | None = None,
) -> DimensionGap:
    """Écart du portefeuille au marché sur une dimension.

    `market_floor` (marché partiel) : poids majorant d'un nom absent du marché, dans les mêmes unités que `market`,
    renormalisé comme lui. Il ne sert qu'à l'affichage et au jugement de sur-pondération : l'active share compare
    les poids connus (absent = 0)."""
    known = _known(portfolio)
    portfolio_total = sum(portfolio.values())
    covered = sum(known.values()) * 100 / portfolio_total if portfolio_total > 0 else 0.0
    w = _normalized(known)
    if not w:
        return DimensionGap(active_share_pct=0.0, covered_pct=0.0, rows=())

    market_known = _known(market)
    market_total = sum(market_known.values())
    b = _normalized(market_known)
    floor = market_floor * 100 / market_total if market_floor is not None and market_total > 0 else None

    rows: list[GapRow] = []
    for name in w.keys() | b.keys():
        mine = w.get(name, 0.0)
        bound = name not in b and floor is not None
        theirs = b.get(name, floor or 0.0)
        rows.append(GapRow(name, mine, theirs, bound, mine - theirs))
    rows.sort(key=lambda r: (-r.gap_pts, r.name))

    # Marché vide : rien en commun (la formule donnerait 50)
    active_share = sum(abs(w.get(n, 0.0) - b.get(n, 0.0)) for n in w.keys() | b.keys()) / 2 if b else 100.0
    return DimensionGap(active_share_pct=active_share, covered_pct=covered, rows=tuple(rows))


def is_overweight(row: GapRow) -> bool:
    return row.portfolio_pct >= OVERWEIGHT_RATIO * row.market_pct and row.gap_pts >= OVERWEIGHT_MIN_POINTS


def is_comparable(gap: DimensionGap) -> bool:
    """Une part du portefeuille est comparable au marché sur cette dimension (composition au moins en partie connue)."""
    return gap.covered_pct > 0


def market_score(gaps: Sequence[DimensionGap]) -> float:
    """100 − moyenne des active shares des dimensions comparables, borné à [0, 100] ; neutre sans dimension
    comparable (une dimension dont rien n'est connu n'est pas « identique au marché »)."""
    comparable = [g for g in gaps if is_comparable(g)]
    if not comparable:
        return NEUTRAL_SCORE
    mean = sum(g.active_share_pct for g in comparable) / len(comparable)
    return round(min(100.0, max(0.0, 100.0 - mean)), 1)
