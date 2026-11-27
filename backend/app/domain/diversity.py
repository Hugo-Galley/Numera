"""Diversification d'un portefeuille par transparence (« look-through ») des ETF : sociétés sous-jacentes,
pays, secteurs, doublons, alertes de concentration et score HHI (sans base)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.core.i18n import tr
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


@dataclass
class LookThrough:
    companies: dict[str, dict[str, Any]] = field(default_factory=dict)
    countries: dict[str, float] = field(default_factory=dict)
    sectors: dict[str, float] = field(default_factory=dict)
    etfs: list[dict[str, Any]] = field(default_factory=list)
    # Origine des compositions utilisées (émetteur, justETF, Yahoo, saisie), par profil
    compositions: dict[int, dict[str, Any]] = field(default_factory=dict)

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


def _spread_lines(target: dict[str, float], lines: Sequence[EtfLine], attribute: str, value_eur: float) -> None:
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


def _add_indirect(out: LookThrough, source: str, value_eur: float,
                  companies: list[tuple[str, str, str | None, float]]) -> None:
    for key, name, ticker, weight in companies:
        value = value_eur * weight / 100.0
        company = out.company(key, name, ticker)
        company["indirect_value_eur"] += value
        if ticker and not company.get("ticker"):
            company["ticker"] = ticker
        company["sources"].append({"source": source, "pct_in_source": round(weight, 2), "value_eur": round(value, 2)})


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
            _spread_lines(target, exposure.lines, attribute, vh_val)
        else:
            spread_weights(target, getattr(described, field_name), vh_val)

    if "top_holdings" not in manual and exposure.lines:
        companies = _line_companies(exposure.lines)
    else:
        companies = _top_holding_companies(etf_profile if "top_holdings" in manual else exposure.profile)
    _add_indirect(out, vh["ticker"], vh_val, companies)


def _direct_line(out: LookThrough, vh: dict[str, Any], security: Security | None) -> None:
    """Une action détenue en direct : pays et secteur du référentiel des titres, sinon « Non renseigné »."""
    vh_val = vh["value_eur"]
    direct_ticker = vh.get("ticker")
    isin = vh.get("isin") or (security.isin if security else None)  # titre retrouvé par ticker : même société
    comp = out.company(normalize_company_key(direct_ticker, vh["name"], isin), vh["name"], direct_ticker)
    comp["direct_value_eur"] += vh_val
    if direct_ticker and not comp.get("ticker"):
        comp["ticker"] = direct_ticker
    comp["sources"].append({
        "source": "En direct",
        "pct_in_source": 100.0,
        "value_eur": round(vh_val, 2),
    })
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
    `exposure_for` donne les lignes d'un profil, ou celles de sa référence d'indice."""
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
            "has_overlap": len(comp["sources"]) > 1,
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


def _company_alerts(companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts = []
    for comp in companies:
        if comp["pct_stocks"] >= 20.0:
            alerts.append({
                "type": "danger",
                "category": "company",
                "title": tr("diversity.company_critical_title", name=comp["name"]),
                "message": tr("diversity.company_critical_message", name=comp["name"], pct_stocks=comp["pct_stocks"], pct_total=comp["pct_total_wealth"]),
                "item_name": comp["name"],
                "value_pct": comp["pct_stocks"],
            })
        elif comp["pct_stocks"] >= 10.0:
            alerts.append({
                "type": "warning",
                "category": "company",
                "title": tr("diversity.company_high_title", name=comp["name"]),
                "message": tr("diversity.company_high_message", name=comp["name"], pct_stocks=comp["pct_stocks"], pct_total=comp["pct_total_wealth"]),
                "item_name": comp["name"],
                "value_pct": comp["pct_stocks"],
            })

    # Doublons
    overlap_companies = [c for c in companies if c["has_overlap"]]
    if overlap_companies:
        sources_str = ", ".join(c["name"] for c in overlap_companies[:3])
        alerts.append({
            "type": "info",
            "category": "overlap",
            "title": tr("diversity.overlap_title", count=len(overlap_companies)),
            "message": tr("diversity.overlap_message", sources=sources_str),
            "item_name": sources_str,
            "value_pct": sum(c["pct_stocks"] for c in overlap_companies[:3]),
        })
    return alerts


def _geography_and_sector_alerts(countries: list[dict[str, Any]], sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts = []
    for country in countries:
        if country["name"] in ("USA", "États-Unis") and country["percentage_stocks"] >= 65.0:
            alerts.append({
                "type": "warning",
                "category": "country",
                "title": tr("diversity.us_title", pct=country["percentage_stocks"]),
                "message": tr("diversity.us_message", pct=country["percentage_stocks"]),
                "item_name": country["name"],
                "value_pct": country["percentage_stocks"],
            })
        elif country["name"] in ("FRA", "France") and country["percentage_stocks"] >= 35.0:
            alerts.append({
                "type": "warning",
                "category": "country",
                "title": tr("diversity.fr_title", pct=country["percentage_stocks"]),
                "message": tr("diversity.fr_message", pct=country["percentage_stocks"]),
                "item_name": country["name"],
                "value_pct": country["percentage_stocks"],
            })
    alerts.extend(
        {
            "type": "warning",
            "category": "sector",
            "title": tr("diversity.sector_title", name=sector["name"], pct=sector["percentage_stocks"]),
            "message": tr("diversity.sector_message", name=sector["name"], pct=sector["percentage_stocks"]),
            "item_name": sector["name"],
            "value_pct": sector["percentage_stocks"],
        }
        for sector in sectors
        if sector["name"] not in (UNKNOWN_LABEL, CASH_LABEL) and sector["percentage_stocks"] >= 30.0
    )
    return alerts


def diversity_alerts(companies: list[dict[str, Any]], countries: list[dict[str, Any]],
                     sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Alertes : société surreprésentée, doublons, concentration géographique, sur-exposition sectorielle."""
    return _company_alerts(companies) + _geography_and_sector_alerts(countries, sectors)
