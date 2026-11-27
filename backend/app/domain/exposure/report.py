"""Forme des champs de risque de `GET /analytics/diversity-scanner` (spec sur-exposition, « Contrat de l'API ») :
expositions et supports, concentration, comparaison au marché, poids du marché par pays et par secteur."""

from collections.abc import Mapping, Sequence
from typing import Any

from app.domain.exposure.concentration import Block
from app.domain.exposure.correlation import Source
from app.domain.exposure.identity import ExposureGroup
from app.domain.exposure.market_gap import DimensionGap

# Lignes servies par dimension (les plus gros écarts, dans un sens ou dans l'autre) : la composition entière d'un
# marché compte des milliers de sociétés. Les alertes, elles, portent sur toutes les lignes.
MARKET_ROWS = 30


def _share(value: float, total: float) -> float:
    return round(value / total * 100, 2) if total > 0 else 0.0


def exposures_payload(groups: Sequence[ExposureGroup], account_names: Mapping[int, str]) -> list[dict[str, Any]]:
    """Une ligne par exposition, avec ses supports (compte, ticker, valeur) du plus gros au plus petit."""
    total = sum(g.value_eur for g in groups)
    return [
        {
            "id": g.key,
            "name": g.name,
            "kind": g.kind,
            "value_eur": round(g.value_eur, 2),
            "weight_pct": _share(g.value_eur, total),
            "supports": [
                {"account_id": h.account_id, "account_name": account_names.get(h.account_id), "ticker": h.ticker,
                 "value_eur": round(h.value_eur, 2)}
                for h in g.holdings
            ],
        }
        for g in groups
    ]


def concentration_payload(groups: Sequence[ExposureGroup], effective_bets: float, blocks: Sequence[Block],
                          pairs_by_source: Mapping[Source, int]) -> dict[str, Any]:
    """Paris indépendants, nombre d'expositions et blocs corrélés (membres nommés comme les expositions)."""
    names = {g.key: g.name for g in groups}
    return {
        "effective_bets": effective_bets,
        "exposures_count": len(groups),
        "blocks": [
            {"members": [names.get(key, key) for key in b.keys], "weight_pct": b.weight_pct, "mean_rho": b.mean_rho}
            for b in blocks
        ],
        "pairs_by_source": dict(pairs_by_source),
    }


def _dimension(gap: DimensionGap) -> dict[str, Any]:
    kept = {id(r) for r in sorted(gap.rows, key=lambda r: abs(r.gap_pts), reverse=True)[:MARKET_ROWS]}
    return {
        "active_share_pct": round(gap.active_share_pct, 2),
        "covered_pct": round(gap.covered_pct, 2),
        "comparable": gap.comparable,
        "rows": [
            {"name": r.name, "portfolio_pct": round(r.portfolio_pct, 2), "market_pct": round(r.market_pct, 2),
             "market_pct_is_upper_bound": r.market_pct_is_upper_bound, "gap_pts": round(r.gap_pts, 2)}
            for r in gap.rows
            if id(r) in kept
        ],
    }


def market_payload(name: str, ticker: str | None, gaps: Mapping[str, DimensionGap] | None) -> dict[str, Any] | None:
    """Référence de marché et écart par dimension ; None sans référence."""
    if gaps is None:
        return None
    return {"name": name, "ticker": ticker, **{dimension: _dimension(gap) for dimension, gap in gaps.items()}}


def with_market_pct(rows: Sequence[dict[str, Any]], gap: DimensionGap | None) -> list[dict[str, Any]]:
    """Ajoute à chaque ligne pays ou secteur le poids du marché (renormalisé sur sa part connue) ; None pour une
    ligne exclue de la comparaison (« Non renseigné », liquidités) ou sans référence."""
    market = {r.name: round(r.market_pct, 2) for r in gap.rows} if gap is not None else {}
    return [{**row, "market_pct": market.get(row["name"])} for row in rows]
