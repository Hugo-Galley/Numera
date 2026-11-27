"""Diversification d'un portefeuille par transparence (« look-through ») des ETF : sociétés sous-jacentes, pays,
secteurs et chemins par lesquels chaque société est détenue (un doublon = au moins deux chemins distincts).

Les alertes et le score, relatifs à une référence de marché, sont dans `domain/exposure/`."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger
from app.domain.etf_composition import EtfLine, is_equity
from app.domain.etf_normalize import UNKNOWN_LABEL
from app.domain.etf_profiles import SOURCE_MANUAL, load_sources
from app.domain.holdings import is_crypto

if TYPE_CHECKING:
    from app.models.etf_profile import EtfProfile
    from app.models.security import Security

CRYPTO_LABEL = "Crypto-actifs"
# Lignes d'un ETF qui ne sont pas des actions : ni pays, ni secteur, ni société
CASH_LABEL = "Liquidités et dérivés"
# Chemin d'une société détenue en direct (les autres chemins portent le nom de l'exposition qui la contient)
DIRECT_SOURCE = "En direct"

logger = get_logger(__name__)


def normalize_company_key(ticker: str | None, name: str | None, isin: str | None = None) -> str:
    """Clé d'une société : l'ISIN d'abord (une action en direct et la même dans un ETF fusionnent), puis le ticker, puis le nom."""
    if isin:
        return f"ISIN:{isin.upper().strip()}"
    if ticker:
        clean_t = ticker.upper().split(".")[0].strip()
        if len(clean_t) >= 2:
            return f"TICKER:{clean_t}"
    if name:
        clean_n = re.sub(r'\b(inc|sa|se|plc|corp|corporation|group|ltd|ag|nv|spa)\b\.?', '', name, flags=re.IGNORECASE).strip().lower()
        clean_n = re.sub(r'[^a-z0-9]', '', clean_n)
        if clean_n:
            return f"NAME:{clean_n}"
    return f"RAW:{ticker or name or 'unknown'}"


def spread_weights(target: dict[str, float], weights_json: str, value_eur: float) -> None:
    """Répartit `value_eur` selon les poids (en %) ; la part non couverte va dans « Non renseigné »."""
    try:
        weights = {k: float(v) for k, v in json.loads(weights_json or "{}").items()}
    except (TypeError, ValueError):
        weights = {}
    for name, weight in weights.items():
        target[name] = target.get(name, 0.0) + value_eur * weight / 100.0
    uncovered = 100.0 - sum(weights.values())
    if uncovered > 0.5:
        target[UNKNOWN_LABEL] = target.get(UNKNOWN_LABEL, 0.0) + value_eur * uncovered / 100.0


@dataclass
class LookThrough:
    companies: dict[str, dict[str, Any]] = field(default_factory=dict)
    countries: dict[str, float] = field(default_factory=dict)
    sectors: dict[str, float] = field(default_factory=dict)
    etfs: list[dict[str, Any]] = field(default_factory=list)
    # Origine des compositions utilisées (émetteur, justETF, Yahoo, saisie), par profil
    compositions: dict[int, dict[str, Any]] = field(default_factory=dict)
    # Valeur des lignes détenues en direct (actions, cryptos : tout ce qui n'est pas un ETF décomposé)
    direct_value_eur: float = 0.0

    @property
    def etf_value_eur(self) -> float:
        """Valeur des positions décomposées comme ETF."""
        return sum(float(e["value_eur"]) for e in self.etfs)

    def company(self, key: str, name: str, ticker: str | None) -> dict[str, Any]:
        if key not in self.companies:
            self.companies[key] = {
                "name": name,
                "ticker": ticker,
                "direct_value_eur": 0.0,
                "indirect_value_eur": 0.0,
                "sources": [],
            }
        return self.companies[key]


@dataclass(frozen=True)
class Exposure:
    """Ce qui décrit l'exposition d'un ETF : son profil, ou celui de la référence d'indice s'il est synthétique."""

    profile: EtfProfile
    lines: Sequence[EtfLine] = ()


def _add(target: dict[str, float], label: str, value: float) -> None:
    target[label] = target.get(label, 0.0) + value


def spread_lines(target: dict[str, float], lines: Sequence[EtfLine], attribute: str, value_eur: float) -> None:
    """Répartit `value_eur` ligne à ligne (pays ou secteur). Les liquidités et dérivés ont leur propre poste, s'il
    est positif ; ce que les lignes ne décrivent pas va dans « Non renseigné »."""
    covered = cash = 0.0
    for line in lines:
        label = getattr(line, attribute)
        if not is_equity(line):
            cash += line.weight
        elif label and label != UNKNOWN_LABEL:
            _add(target, label, value_eur * line.weight / 100.0)
            covered += line.weight
    if cash > 0:
        _add(target, CASH_LABEL, value_eur * cash / 100.0)
    uncovered = 100.0 - covered - max(cash, 0.0)
    if uncovered > 0.5:
        _add(target, UNKNOWN_LABEL, value_eur * uncovered / 100.0)


def _line_companies(lines: Sequence[EtfLine]) -> list[tuple[str, str, str | None, float]]:
    """(clé, nom, ticker, poids) des actions d'un ETF, une entrée par société."""
    companies: dict[str, tuple[str, str | None, float]] = {}
    for line in lines:
        if not is_equity(line) or line.weight <= 0:
            continue
        key = normalize_company_key(line.ticker, line.name, line.isin)
        name, ticker, weight = companies.get(key, (line.name, line.ticker, 0.0))
        companies[key] = (name, ticker or line.ticker, weight + line.weight)
    return [(key, *company) for key, company in companies.items()]


def _top_holding_companies(profile: EtfProfile) -> list[tuple[str, str, str | None, float]]:
    """Mêmes tuples depuis les premières lignes enregistrées sur le profil (sources sans détail, saisie)."""
    companies = []
    try:
        for item in json.loads(profile.top_holdings or "[]"):
            name, ticker = item["name"], item.get("ticker")
            key = normalize_company_key(ticker, name, item.get("isin"))
            companies.append((key, name, ticker, float(item.get("weight", 0.0))))
    except (ValueError, KeyError, TypeError, AttributeError) as e:  # JSON ou ligne de composition mal formés
        logger.warning(f"Error parsing ETF holdings for {profile.name}: {e}")
    return companies


def _add_source(company: dict[str, Any], source: str, pct: float, value: float) -> None:
    """Un chemin de plus vers la société ; deux supports d'une même exposition forment un seul chemin."""
    for existing in company["sources"]:
        if existing["source"] == source:
            existing["value_eur"] = round(existing["value_eur"] + value, 2)
            return
    company["sources"].append({"source": source, "pct_in_source": round(pct, 2), "value_eur": round(value, 2)})


def _add_indirect(out: LookThrough, source: str, value_eur: float,
                  companies: list[tuple[str, str, str | None, float]]) -> None:
    for key, name, ticker, weight in companies:
        value = value_eur * weight / 100.0
        company = out.company(key, name, ticker)
        company["indirect_value_eur"] += value
        if ticker and not company.get("ticker"):
            company["ticker"] = ticker
        _add_source(company, source, weight, value)


def _composition_origin(held: EtfProfile, data: EtfProfile) -> dict[str, Any]:
    """Synthétique : réplication, indice et référence viennent du fonds détenu ; source, date, lignes et
    couverture de `data`, le profil dont les chiffres sont utilisés."""
    return {
        "provider": data.provider,
        "replication": held.replication,
        "index_name": held.index_name,
        "exposure_profile_id": held.exposure_profile_id,
        "exposure_profile_name": data.name if data.id == held.exposure_profile_id else None,
        "composition_as_of": data.composition_as_of,
        "coverage_pct": data.coverage_pct,
        "lines_count": data.lines_count,
    }


def _decompose_etf(out: LookThrough, vh: dict[str, Any], etf_profile: EtfProfile, exposure: Exposure) -> None:
    """Un ETF : sa valeur est répartie entre ses pays, secteurs et sociétés, ligne à ligne quand elles sont connues.

    Champ par champ : une saisie manuelle du profil détenu l'emporte, puis les lignes, puis les agrégats."""
    vh_val = vh["value_eur"]
    out.etfs.append({
        "ticker": vh["ticker"],
        "name": vh["name"],
        "value_eur": vh_val,
        "profile_name": etf_profile.name,
    })
    manual = {name for name, origin in load_sources(etf_profile).items() if origin == SOURCE_MANUAL}
    if etf_profile.id not in out.compositions:
        origin = load_sources(exposure.profile) | dict.fromkeys(manual, SOURCE_MANUAL)
        out.compositions[etf_profile.id] = {
            "profile_id": etf_profile.id,
            "profile_name": etf_profile.name,
            "tickers": [],
            "value_eur": 0.0,
            "sources": origin,
            "refreshed_at": exposure.profile.composition_refreshed_at,
            **_composition_origin(etf_profile, exposure.profile),
        }
    out.compositions[etf_profile.id]["tickers"].append(vh["ticker"])
    out.compositions[etf_profile.id]["value_eur"] += vh_val

    for field_name, attribute, target in (("countries", "country", out.countries), ("sectors", "sector", out.sectors)):
        described = etf_profile if field_name in manual else exposure.profile
        if field_name not in manual and exposure.lines:
            spread_lines(target, exposure.lines, attribute, vh_val)
        else:
            spread_weights(target, getattr(described, field_name), vh_val)

    if "top_holdings" not in manual and exposure.lines:
        companies = _line_companies(exposure.lines)
    else:
        companies = _top_holding_companies(etf_profile if "top_holdings" in manual else exposure.profile)
    _add_indirect(out, vh.get("source_label") or vh["ticker"], vh_val, companies)


def _direct_line(out: LookThrough, vh: dict[str, Any], security: Security | None) -> None:
    """Une action détenue en direct : pays et secteur du référentiel des titres, sinon « Non renseigné »."""
    vh_val = vh["value_eur"]
    out.direct_value_eur += vh_val
    direct_ticker = vh.get("ticker")
    isin = vh.get("isin") or (security.isin if security else None)  # titre retrouvé par ticker : même société
    comp = out.company(normalize_company_key(direct_ticker, vh["name"], isin), vh["name"], direct_ticker)
    comp["direct_value_eur"] += vh_val
    if direct_ticker and not comp.get("ticker"):
        comp["ticker"] = direct_ticker
    _add_source(comp, DIRECT_SOURCE, 100.0, vh_val)
    country = (security.country if security else None) or UNKNOWN_LABEL
    sector = (security.sector if security else None) or UNKNOWN_LABEL
    out.countries[country] = out.countries.get(country, 0.0) + vh_val
    out.sectors[sector] = out.sectors.get(sector, 0.0) + vh_val


def look_through(valued_holdings: list[dict[str, Any]],
                 profile_for: Callable[[dict[str, Any]], EtfProfile | None],
                 securities: dict[str, Security] | None = None,
                 exposure_for: Callable[[EtfProfile], Exposure] = Exposure) -> LookThrough:
    """Agrège les positions valorisées (> 0) : un ETF est décomposé selon son profil, une crypto compte dans son
    propre secteur, une action reste en direct (`securities` : titres par ISIN, ou par ticker à défaut d'ISIN).
    `exposure_for` donne les lignes d'un profil, ou celles de sa référence d'indice. `source_label` (facultatif) :
    nom de l'exposition de la position, chemin des sociétés de ses lignes (le ticker à défaut)."""
    out = LookThrough()
    securities = securities or {}
    for vh in valued_holdings:
        if vh["value_eur"] <= 0:
            continue
        etf_profile = profile_for(vh)
        if etf_profile:
            _decompose_etf(out, vh, etf_profile, exposure_for(etf_profile))
        elif is_crypto(vh.get("quote_type"), vh["ticker"]):
            out.sectors[CRYPTO_LABEL] = out.sectors.get(CRYPTO_LABEL, 0.0) + vh["value_eur"]
            out.direct_value_eur += vh["value_eur"]
        else:
            _direct_line(out, vh, securities.get(vh.get("isin") or vh["ticker"].upper()))
    return out


def _pct(value: float, total: float) -> float:
    return round((value / total * 100.0), 2) if total > 0 else 0.0


def top_companies(companies: dict[str, dict[str, Any]], total_stocks: float, total_wealth: float) -> list[dict[str, Any]]:
    rows = []
    for comp in companies.values():
        total_comp_eur = round(comp["direct_value_eur"] + comp["indirect_value_eur"], 2)
        rows.append({
            "name": comp["name"],
            "ticker": comp["ticker"],
            "direct_value_eur": round(comp["direct_value_eur"], 2),
            "indirect_value_eur": round(comp["indirect_value_eur"], 2),
            "total_value_eur": total_comp_eur,
            "pct_stocks": _pct(total_comp_eur, total_stocks),
            "pct_total_wealth": _pct(total_comp_eur, total_wealth),
            "sources": comp["sources"],
            "has_overlap": len({s["source"] for s in comp["sources"]}) > 1,
        })
    rows.sort(key=lambda c: c["total_value_eur"], reverse=True)
    return rows


def exposure_rows(values: dict[str, float], total_stocks: float, total_wealth: float) -> list[dict[str, Any]]:
    """Exposition par pays ou par secteur, en valeur et en % des actions / du patrimoine, décroissante."""
    rows: list[dict[str, Any]] = [
        {
            "name": name,
            "value_eur": round(value, 2),
            "percentage_stocks": _pct(value, total_stocks),
            "percentage_total_wealth": _pct(value, total_wealth),
        }
        for name, value in values.items()
    ]
    rows.sort(key=lambda x: x["value_eur"], reverse=True)
    return rows
