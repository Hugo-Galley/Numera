"""Diversification d'un portefeuille par transparence (« look-through ») des ETF : sociétés sous-jacentes,
pays, secteurs, doublons, alertes de concentration et score HHI (sans base)."""
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.core.logging import get_logger
from app.domain.etf_profiles import load_sources
from app.models.etf_profile import EtfProfile

logger = get_logger(__name__)

UNKNOWN_LABEL = "Non renseigné"


def normalize_company_key(ticker: Optional[str], name: Optional[str]) -> str:
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


def spread_weights(target: Dict[str, float], weights_json: str, value_eur: float) -> None:
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


def hhi_score(weights: List[float]) -> float:
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
        return "Concentration critique"
    if score < 60:
        return "Concentration modérée"
    if score < 80:
        return "Bonne diversification globale"
    return "Excellente diversification"


@dataclass
class LookThrough:
    companies: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    countries: Dict[str, float] = field(default_factory=dict)
    sectors: Dict[str, float] = field(default_factory=dict)
    etfs: List[Dict[str, Any]] = field(default_factory=list)
    # Origine des compositions utilisées (Yahoo, préréglage, saisie), par profil
    compositions: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    def company(self, key: str, name: str, ticker: Optional[str]) -> Dict[str, Any]:
        if key not in self.companies:
            self.companies[key] = {
                "name": name,
                "ticker": ticker,
                "direct_value_eur": 0.0,
                "indirect_value_eur": 0.0,
                "sources": [],
            }
        return self.companies[key]


def _decompose_etf(out: LookThrough, vh: Dict[str, Any], etf_profile: EtfProfile) -> None:
    """Un ETF : sa valeur est répartie entre ses pays, secteurs et premières lignes."""
    vh_val = vh["value_eur"]
    out.etfs.append({
        "ticker": vh["ticker"],
        "name": vh["name"],
        "value_eur": vh_val,
        "profile_name": etf_profile.name,
    })
    if etf_profile.id not in out.compositions:
        out.compositions[etf_profile.id] = {
            "profile_id": etf_profile.id,
            "profile_name": etf_profile.name,
            "tickers": [],
            "value_eur": 0.0,
            "sources": load_sources(etf_profile),
            "refreshed_at": etf_profile.composition_refreshed_at,
        }
    out.compositions[etf_profile.id]["tickers"].append(vh["ticker"])
    out.compositions[etf_profile.id]["value_eur"] += vh_val

    spread_weights(out.countries, etf_profile.countries, vh_val)
    spread_weights(out.sectors, etf_profile.sectors, vh_val)

    # Top holdings look-through
    try:
        for h_item in json.loads(etf_profile.top_holdings):
            h_name = h_item["name"]
            h_ticker = h_item.get("ticker")
            h_weight = float(h_item.get("weight", 0.0))
            h_val = vh_val * (h_weight / 100.0)
            comp = out.company(normalize_company_key(h_ticker, h_name), h_name, h_ticker)
            comp["indirect_value_eur"] += h_val
            if h_ticker and not comp.get("ticker"):
                comp["ticker"] = h_ticker
            comp["sources"].append({
                "source": vh["ticker"],
                "pct_in_source": round(h_weight, 2),
                "value_eur": round(h_val, 2),
            })
    except Exception as e:
        logger.warning(f"Error parsing ETF holdings for {etf_profile.name}: {e}")


def _direct_line(out: LookThrough, vh: Dict[str, Any]) -> None:
    """Une action détenue en direct (pays et secteur par défaut)."""
    vh_val = vh["value_eur"]
    direct_ticker = vh.get("ticker")
    comp = out.company(normalize_company_key(direct_ticker, vh["name"]), vh["name"], direct_ticker)
    comp["direct_value_eur"] += vh_val
    if direct_ticker and not comp.get("ticker"):
        comp["ticker"] = direct_ticker
    comp["sources"].append({
        "source": "En direct",
        "pct_in_source": 100.0,
        "value_eur": round(vh_val, 2),
    })
    out.countries["Autres"] = out.countries.get("Autres", 0.0) + vh_val
    out.sectors["Actions directes"] = out.sectors.get("Actions directes", 0.0) + vh_val


def look_through(valued_holdings: List[Dict[str, Any]],
                 profile_for: Callable[[Dict[str, Any]], Optional[EtfProfile]]) -> LookThrough:
    """Agrège les positions valorisées (> 0) : un ETF est décomposé selon son profil, une action reste en direct."""
    out = LookThrough()
    for vh in valued_holdings:
        if vh["value_eur"] <= 0:
            continue
        etf_profile = profile_for(vh)
        if etf_profile:
            _decompose_etf(out, vh, etf_profile)
        else:
            _direct_line(out, vh)
    return out


def _pct(value: float, total: float) -> float:
    return round((value / total * 100.0), 2) if total > 0 else 0.0


def top_companies(companies: Dict[str, Dict[str, Any]], total_stocks: float, total_wealth: float) -> List[Dict[str, Any]]:
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


def exposure_rows(values: Dict[str, float], total_stocks: float, total_wealth: float) -> List[Dict[str, Any]]:
    """Exposition par pays ou par secteur, en valeur et en % des actions / du patrimoine, décroissante."""
    rows = [
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


def _company_alerts(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    alerts = []
    for comp in companies:
        if comp["pct_stocks"] >= 20.0:
            alerts.append({
                "type": "danger",
                "category": "company",
                "title": f"Concentration critique sur {comp['name']}",
                "message": f"{comp['name']} pèse {comp['pct_stocks']}% de votre portefeuille boursier ({comp['pct_total_wealth']}% du patrimoine total). Ce niveau de concentration sur un seul titre présente un risque spécifique élevé.",
                "item_name": comp["name"],
                "value_pct": comp["pct_stocks"],
            })
        elif comp["pct_stocks"] >= 10.0:
            alerts.append({
                "type": "warning",
                "category": "company",
                "title": f"Forte exposition sur {comp['name']}",
                "message": f"{comp['name']} représente {comp['pct_stocks']}% de vos actions/ETFs ({comp['pct_total_wealth']}% du patrimoine total).",
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
            "title": f"Doublons d'exposition détectés ({len(overlap_companies)} titres)",
            "message": f"Vous détenez des titres simultanément en direct et/ou à travers plusieurs ETFs (notamment {sources_str}). Leur pondération réelle s'additionne discrètement.",
            "item_name": sources_str,
            "value_pct": sum(c["pct_stocks"] for c in overlap_companies[:3]),
        })
    return alerts


def _geography_and_sector_alerts(countries: List[Dict[str, Any]], sectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    alerts = []
    for country in countries:
        if country["name"] in ("USA", "États-Unis") and country["percentage_stocks"] >= 65.0:
            alerts.append({
                "type": "warning",
                "category": "country",
                "title": f"Forte prépondérance américaine ({country['percentage_stocks']}%)",
                "message": f"{country['percentage_stocks']}% de votre exposition boursière est concentrée sur les États-Unis. Sensibilité accrue au dollar et aux marchés US.",
                "item_name": country["name"],
                "value_pct": country["percentage_stocks"],
            })
        elif country["name"] in ("FRA", "France") and country["percentage_stocks"] >= 35.0:
            alerts.append({
                "type": "warning",
                "category": "country",
                "title": f"Biais domestique français ({country['percentage_stocks']}%)",
                "message": f"Votre portefeuille actions alloue {country['percentage_stocks']}% à la France. Pensez à diversifier géographiquement.",
                "item_name": country["name"],
                "value_pct": country["percentage_stocks"],
            })
    for sector in sectors:
        if sector["name"] != UNKNOWN_LABEL and sector["percentage_stocks"] >= 30.0:
            alerts.append({
                "type": "warning",
                "category": "sector",
                "title": f"Sur-exposition sectorielle : {sector['name']} ({sector['percentage_stocks']}%)",
                "message": f"Le secteur {sector['name']} domine {sector['percentage_stocks']}% de vos investissements en actions.",
                "item_name": sector["name"],
                "value_pct": sector["percentage_stocks"],
            })
    return alerts


def diversity_alerts(companies: List[Dict[str, Any]], countries: List[Dict[str, Any]],
                     sectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Alertes : société surreprésentée, doublons, concentration géographique, sur-exposition sectorielle."""
    return _company_alerts(companies) + _geography_and_sector_alerts(countries, sectors)
