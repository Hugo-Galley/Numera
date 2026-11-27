"""Règles de la composition d'un ETF publiée par son émetteur (calculs purs, sans base ni réseau) :
seuil de vraisemblance, agrégats tirés des lignes, couverture, fonds synthétiques et indices de référence."""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple, Protocol

from app.domain.etf_normalize import UNKNOWN_LABEL, is_equity_line

# Un émetteur dont les lignes totalisent moins que ce poids a changé de format : sa réponse est écartée
MIN_TOTAL_WEIGHT = 50.0
TOP_HOLDINGS = 10
# Sources qui publient toutes les lignes : seules à être redemandées en premier quand elles ont déjà répondu
LINE_SOURCES = ("ishares", "amundi", "spdr")

# Indice -> ISIN de son ETF physique de référence (des identifiants seulement, aucun poids)
INDEX_REFERENCES: dict[str, str] = json.loads(
    Path(__file__).with_name("index_references.json").read_text(encoding="utf-8"))


class EtfLine(Protocol):
    """Une ligne de composition, quelle que soit son origine (émetteur ou base)."""

    @property
    def isin(self) -> str | None: ...
    @property
    def ticker(self) -> str | None: ...
    @property
    def name(self) -> str: ...
    @property
    def weight(self) -> float: ...
    @property
    def country(self) -> str | None: ...
    @property
    def sector(self) -> str: ...
    @property
    def asset_class(self) -> str: ...


class EtfConstituentRow(NamedTuple):
    """Ligne relue de la base (colonnes seules, sans objet ORM)."""

    isin: str | None
    ticker: str | None
    name: str
    weight: float
    country: str | None
    sector: str
    asset_class: str


def is_usable(lines: Sequence[EtfLine]) -> bool:
    return sum(line.weight for line in lines) >= MIN_TOTAL_WEIGHT


def is_equity(line: EtfLine) -> bool:
    return is_equity_line(line.asset_class, None)


def _capped(total: float) -> float:
    return round(min(100.0, max(0.0, total)), 2)


def _grouped(lines: Sequence[EtfLine], key: str) -> dict[str, float]:
    totals: dict[str, float] = {}
    for line in lines:
        label = getattr(line, key)
        if label and label != UNKNOWN_LABEL:  # la part non renseignée reste hors des agrégats : elle n'est pas couverte
            totals[label] = totals.get(label, 0.0) + line.weight
    return {label: round(weight, 4) for label, weight in sorted(totals.items(), key=lambda kv: -kv[1]) if weight > 0}


def aggregate_lines(lines: Sequence[EtfLine]) -> dict[str, Any]:
    """Pays, secteurs et dix premières lignes, calculés sur les lignes actions."""
    equities = [line for line in lines if is_equity(line)]
    top = sorted(equities, key=lambda line: line.weight, reverse=True)[:TOP_HOLDINGS]
    return {
        "countries": _grouped(equities, "country"),
        "sectors": _grouped(equities, "sector"),
        "top_holdings": [{"name": x.name, "ticker": x.ticker, "isin": x.isin, "weight": x.weight} for x in top],
    }


def coverage_of_lines(lines: Sequence[EtfLine]) -> float:
    """Part du fonds investie en actions, en %."""
    return _capped(sum(line.weight for line in lines if is_equity(line)))


def coverage_of_aggregates(values: dict[str, Any]) -> float:
    """Part du fonds décrite par des agrégats : la mieux couverte des répartitions, sinon les premières lignes."""
    spread = max((sum((values.get(field) or {}).values()) for field in ("countries", "sectors")), default=0.0)
    return _capped(spread or sum(h.get("weight", 0.0) for h in values.get("top_holdings") or []))


def looks_synthetic(name: str) -> bool:
    """Faute de mode de réplication publié, le mot « Swap » du nom suffit à écarter le panier détenu."""
    return "swap" in name.lower().split()
