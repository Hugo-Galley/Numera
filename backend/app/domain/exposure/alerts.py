"""Alertes du scanner de diversification (spec sur-exposition § 5 et 6), toutes calculées : aucun pays, aucun
secteur, aucun plafond écrit ici.

- `overweight` : une ligne d'une dimension (sociétés, secteurs, pays) sur-pondérée par rapport au marché ;
- `correlated_block` : un bloc de lignes corrélées sans fonds (lignes en direct, crypto), qui pèse plus que son
  poids de marché + `OVERWEIGHT_MIN_POINTS`, ou n'a pas d'équivalent de marché (crypto) ; un bloc qui contient un
  fonds relève du stock picking redondant ;
- `redundant_pick` : une action en direct déjà détenue via les fonds et corrélée au cœur du portefeuille ;
- `overlap` (info) : des sociétés détenues par des chemins différents."""

from collections.abc import Mapping, Sequence
from typing import Any

from app.core.i18n import format_money, format_number, tr
from app.domain.exposure.concentration import Block
from app.domain.exposure.identity import ExposureGroup
from app.domain.exposure.market_gap import DimensionGap, GapRow, is_overweight
from app.domain.exposure.params import OVERWEIGHT_MIN_POINTS

DIMENSIONS = ("companies", "sectors", "countries")
# Sociétés citées dans le message de doublons
OVERLAP_NAMES_SHOWN = 3


def _pct(value: float) -> str:
    return format_number(value, 1)


def _overweight(dimension: str, row: GapRow) -> dict[str, Any]:
    params = {"name": row.name, "pct": _pct(row.portfolio_pct), "market": _pct(row.market_pct)}
    bound = tr("diversity.upper_bound") if row.market_pct_is_upper_bound else ""
    return {
        "type": "warning",
        "category": "overweight",
        "dimension": dimension,
        "title": tr("diversity.overweight_title", name=row.name, pct=params["pct"]),
        "message": tr("diversity.overweight_message", bound=bound, **params),
        "item_name": row.name,
        "value_pct": round(row.portfolio_pct, 2),
    }


def _block(block: Block, groups_by_key: Mapping[str, ExposureGroup],
           market_weights: Mapping[str, float] | None) -> dict[str, Any] | None:
    members = [groups_by_key[key] for key in block.keys if key in groups_by_key]
    if not members or any(g.kind == "fund" for g in members):
        return None
    # Bloc qui a un équivalent de marché (toutes ses lignes y ont un poids) : alerte seulement s'il pèse au moins
    # ce poids + OVERWEIGHT_MIN_POINTS. Sans équivalent (crypto) : alerte systématique.
    has_equivalent = market_weights is not None and all(g.key in market_weights for g in members)
    if has_equivalent and block.weight_pct < sum((market_weights or {})[g.key] for g in members) + OVERWEIGHT_MIN_POINTS:
        return None
    names = " + ".join(g.name for g in members)
    pct = _pct(block.weight_pct)
    return {
        "type": "warning",
        "category": "correlated_block",
        "title": tr("diversity.block_title", pct=pct),
        "message": tr("diversity.block_message", names=names, pct=pct, rho=format_number(block.mean_rho, 2)),
        "item_name": names,
        "value_pct": round(block.weight_pct, 2),
    }


def _redundant(pick: Mapping[str, Any]) -> dict[str, Any]:
    rho = pick.get("correlation_with_core")
    return {
        "type": "warning",
        "category": "redundant_pick",
        "title": tr("diversity.redundant_pick_title", name=pick["name"]),
        "message": tr("diversity.redundant_pick_message", name=pick["name"],
                      indirect=format_money(float(pick["indirect_value_eur"])),
                      rho=format_number(float(rho or 0.0), 2)),
        "item_name": pick["name"],
        "value_pct": round(float(pick.get("indirect_pct", 0.0)), 2),
    }


def _overlap(names: Sequence[str]) -> dict[str, Any]:
    shown = ", ".join(names[:OVERLAP_NAMES_SHOWN])
    return {
        "type": "info",
        "category": "overlap",
        "title": tr("diversity.overlap_title", count=len(names)),
        "message": tr("diversity.overlap_message", sources=shown),
        "item_name": shown,
        "value_pct": 0.0,
    }


def market_alerts(
    gaps: Mapping[str, DimensionGap] | None,
    blocks: Sequence[Block],
    groups_by_key: Mapping[str, ExposureGroup],
    stock_picking: Sequence[Mapping[str, Any]],
    overlap_names: Sequence[str],
    market_weights: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Alertes dans l'ordre : sur-pondérations (par dimension), blocs corrélés, stock picking redondant, doublons."""
    alerts: list[dict[str, Any]] = []
    for dimension in DIMENSIONS:
        gap = (gaps or {}).get(dimension)
        if gap is not None and gap.comparable:
            alerts.extend(_overweight(dimension, row) for row in gap.rows if is_overweight(row))
    for block in blocks:
        alert = _block(block, groups_by_key, market_weights)
        if alert is not None:
            alerts.append(alert)
    alerts.extend(_redundant(pick) for pick in stock_picking if pick.get("redundant"))
    if overlap_names:
        alerts.append(_overlap(overlap_names))
    return alerts
