import json
import re
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding

logger = get_logger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# Thematic Archetypes used to auto-decompose unknown funds/ETFs when detailed scrapers are unavailable
ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "tech": {
        "countries": {"USA": 85.0, "TWN": 5.0, "NLD": 4.0, "KOR": 3.0, "Autres": 3.0},
        "sectors": {"Technologie": 82.0, "Services de communication": 12.0, "Consommation discrétionnaire": 6.0},
        "top_holdings": [
            {"name": "Apple", "ticker": "AAPL", "weight": 9.5},
            {"name": "Microsoft", "ticker": "MSFT", "weight": 9.0},
            {"name": "Nvidia", "ticker": "NVDA", "weight": 8.5},
            {"name": "Broadcom", "ticker": "AVGO", "weight": 4.8},
            {"name": "Alphabet (Google)", "ticker": "GOOGL", "weight": 4.5},
            {"name": "Amazon", "ticker": "AMZN", "weight": 4.2},
            {"name": "Meta Platforms", "ticker": "META", "weight": 4.0},
            {"name": "TSMC", "ticker": "TSM", "weight": 3.5},
            {"name": "ASML", "ticker": "ASML.AS", "weight": 3.0},
            {"name": "Tesla", "ticker": "TSLA", "weight": 2.8},
        ],
    },
    "sp500": {
        "countries": {"USA": 100.0},
        "sectors": {"Technologie": 31.0, "Finance": 13.5, "Santé": 12.0, "Consommation discrétionnaire": 10.5, "Industrie": 8.5, "Services de communication": 8.5, "Autres": 16.0},
        "top_holdings": [
            {"name": "Apple", "ticker": "AAPL", "weight": 7.1},
            {"name": "Microsoft", "ticker": "MSFT", "weight": 6.6},
            {"name": "Nvidia", "ticker": "NVDA", "weight": 6.2},
            {"name": "Amazon", "ticker": "AMZN", "weight": 3.8},
            {"name": "Alphabet (Google)", "ticker": "GOOGL", "weight": 3.6},
            {"name": "Meta Platforms", "ticker": "META", "weight": 2.5},
            {"name": "Berkshire Hathaway", "ticker": "BRK-B", "weight": 1.7},
            {"name": "Eli Lilly", "ticker": "LLY", "weight": 1.5},
            {"name": "JPMorgan Chase", "ticker": "JPM", "weight": 1.3},
            {"name": "Tesla", "ticker": "TSLA", "weight": 1.3},
        ],
    },
    "europe": {
        "countries": {"GBR": 22.0, "FRA": 18.0, "CHE": 15.0, "DEU": 13.0, "NLD": 7.5, "DNK": 5.0, "SWE": 4.5, "Autres": 15.0},
        "sectors": {"Finance": 18.5, "Santé": 16.0, "Industrie": 15.5, "Consommation discrétionnaire": 11.0, "Biens de consommation de base": 9.5, "Technologie": 8.0, "Autres": 21.5},
        "top_holdings": [
            {"name": "Novo Nordisk", "ticker": "NOVO-B.CO", "weight": 3.8},
            {"name": "ASML", "ticker": "ASML.AS", "weight": 3.4},
            {"name": "Nestlé", "ticker": "NESN.SW", "weight": 2.8},
            {"name": "LVMH", "ticker": "MC.PA", "weight": 2.2},
            {"name": "AstraZeneca", "ticker": "AZN.L", "weight": 2.1},
            {"name": "SAP", "ticker": "SAP.DE", "weight": 2.0},
            {"name": "Novartis", "ticker": "NOVN.SW", "weight": 1.9},
            {"name": "Roche", "ticker": "ROG.SW", "weight": 1.8},
            {"name": "TotalEnergies", "ticker": "TTE.PA", "weight": 1.6},
            {"name": "Schneider Electric", "ticker": "SU.PA", "weight": 1.5},
        ],
    },
    "emerging": {
        "countries": {"CHN": 26.0, "IND": 21.0, "TWN": 18.0, "KOR": 11.0, "BRA": 5.5, "SAU": 4.0, "ZAF": 3.0, "Autres": 11.5},
        "sectors": {"Technologie": 26.0, "Finance": 22.0, "Consommation discrétionnaire": 13.5, "Services de communication": 9.0, "Industrie": 7.0, "Matériaux": 6.5, "Autres": 16.0},
        "top_holdings": [
            {"name": "TSMC", "ticker": "TSM", "weight": 9.8},
            {"name": "Tencent", "ticker": "0700.HK", "weight": 4.3},
            {"name": "Samsung Electronics", "ticker": "005930.KS", "weight": 3.9},
            {"name": "Alibaba", "ticker": "BABA", "weight": 2.4},
            {"name": "Reliance Industries", "ticker": "RELIANCE.NS", "weight": 1.5},
            {"name": "Meituan", "ticker": "3690.HK", "weight": 1.2},
            {"name": "ICICI Bank", "ticker": "IBN", "weight": 1.1},
            {"name": "Infosys", "ticker": "INFY", "weight": 1.0},
            {"name": "SK Hynix", "ticker": "000660.KS", "weight": 0.9},
            {"name": "Petrobras", "ticker": "PBR", "weight": 0.8},
        ],
    },
    "health": {
        "countries": {"USA": 70.0, "CHE": 10.0, "DNK": 6.0, "GBR": 5.0, "FRA": 4.0, "Autres": 5.0},
        "sectors": {"Santé": 95.0, "Autres": 5.0},
        "top_holdings": [
            {"name": "Eli Lilly", "ticker": "LLY", "weight": 10.5},
            {"name": "Novo Nordisk", "ticker": "NOVO-B.CO", "weight": 7.5},
            {"name": "UnitedHealth Group", "ticker": "UNH", "weight": 7.0},
            {"name": "Johnson & Johnson", "ticker": "JNJ", "weight": 5.5},
            {"name": "AbbVie", "ticker": "ABBV", "weight": 4.8},
            {"name": "Merck & Co", "ticker": "MRK", "weight": 4.5},
            {"name": "AstraZeneca", "ticker": "AZN.L", "weight": 4.0},
            {"name": "Novartis", "ticker": "NOVN.SW", "weight": 3.8},
            {"name": "Roche", "ticker": "ROG.SW", "weight": 3.5},
            {"name": "Thermo Fisher Scientific", "ticker": "TMO", "weight": 3.2},
        ],
    },
    "realestate": {
        "countries": {"USA": 65.0, "JPN": 8.0, "GBR": 5.0, "AUS": 5.0, "FRA": 4.0, "SGP": 3.0, "Autres": 10.0},
        "sectors": {"Immobilier": 96.0, "Autres": 4.0},
        "top_holdings": [
            {"name": "Prologis", "ticker": "PLD", "weight": 7.5},
            {"name": "American Tower", "ticker": "AMT", "weight": 6.2},
            {"name": "Equinix", "ticker": "EQIX", "weight": 5.8},
            {"name": "Welltower", "ticker": "WELL", "weight": 4.2},
            {"name": "Simon Property Group", "ticker": "SPG", "weight": 3.8},
            {"name": "Public Storage", "ticker": "PSA", "weight": 3.5},
            {"name": "Realty Income", "ticker": "O", "weight": 3.2},
            {"name": "Digital Realty", "ticker": "DLR", "weight": 3.0},
            {"name": "Goodman Group", "ticker": "GMG.AX", "weight": 2.5},
            {"name": "Vonovia", "ticker": "VNA.DE", "weight": 1.8},
        ],
    },
    "bonds": {
        "countries": {"USA": 45.0, "FRA": 12.0, "DEU": 10.0, "JPN": 8.0, "ITA": 6.0, "GBR": 5.0, "Autres": 14.0},
        "sectors": {"Obligations / Emprunts d'État": 65.0, "Obligations d'entreprises (Corporate)": 30.0, "Autres": 5.0},
        "top_holdings": [
            {"name": "US Treasury 10Y", "ticker": "US10Y", "weight": 12.0},
            {"name": "US Treasury 5Y", "ticker": "US5Y", "weight": 10.0},
            {"name": "OAT France 10Y", "ticker": "FR10Y", "weight": 6.0},
            {"name": "German Bund 10Y", "ticker": "DE10Y", "weight": 5.0},
            {"name": "US Treasury 30Y", "ticker": "US30Y", "weight": 4.5},
            {"name": "Italian BTP 10Y", "ticker": "IT10Y", "weight": 3.5},
            {"name": "UK Gilt 10Y", "ticker": "GB10Y", "weight": 3.0},
            {"name": "JPMorgan Corporate Bond", "ticker": "JPM.BOND", "weight": 2.5},
            {"name": "BNP Paribas Corporate Bond", "ticker": "BNP.BOND", "weight": 2.0},
            {"name": "TotalEnergies Corporate Bond", "ticker": "TTE.BOND", "weight": 1.5},
        ],
    },
    "multi_asset": {
        "countries": {"USA": 45.0, "FRA": 18.0, "DEU": 8.0, "GBR": 6.0, "JPN": 5.0, "CHE": 4.0, "Autres": 14.0},
        "sectors": {"Technologie": 18.0, "Finance": 16.0, "Obligations & Emprunts": 25.0, "Santé": 11.0, "Industrie": 10.0, "Immobilier": 8.0, "Autres": 12.0},
        "top_holdings": [
            {"name": "Microsoft", "ticker": "MSFT", "weight": 4.2},
            {"name": "Apple", "ticker": "AAPL", "weight": 3.8},
            {"name": "Nvidia", "ticker": "NVDA", "weight": 3.5},
            {"name": "TotalEnergies", "ticker": "TTE.PA", "weight": 2.4},
            {"name": "LVMH", "ticker": "MC.PA", "weight": 2.2},
            {"name": "Schneider Electric", "ticker": "SU.PA", "weight": 2.0},
            {"name": "ASML", "ticker": "ASML.AS", "weight": 1.8},
            {"name": "Air Liquide", "ticker": "AI.PA", "weight": 1.7},
            {"name": "Sanofi", "ticker": "SAN.PA", "weight": 1.6},
            {"name": "Amazon", "ticker": "AMZN", "weight": 1.5},
        ],
    },
    "world": {
        "countries": {"USA": 71.0, "JPN": 5.5, "GBR": 3.8, "CAN": 3.1, "FRA": 2.8, "CHE": 2.4, "DEU": 2.1, "Autres": 9.3},
        "sectors": {"Technologie": 25.0, "Finance": 15.0, "Santé": 12.0, "Industrie": 11.0, "Consommation discrétionnaire": 10.0, "Services de communication": 7.5, "Autres": 19.5},
        "top_holdings": [
            {"name": "Apple", "ticker": "AAPL", "weight": 4.8},
            {"name": "Microsoft", "ticker": "MSFT", "weight": 4.3},
            {"name": "Nvidia", "ticker": "NVDA", "weight": 4.1},
            {"name": "Alphabet (Google)", "ticker": "GOOGL", "weight": 2.9},
            {"name": "Amazon", "ticker": "AMZN", "weight": 2.6},
            {"name": "Meta Platforms", "ticker": "META", "weight": 1.9},
            {"name": "Broadcom", "ticker": "AVGO", "weight": 1.3},
            {"name": "Tesla", "ticker": "TSLA", "weight": 1.2},
            {"name": "Eli Lilly", "ticker": "LLY", "weight": 1.1},
            {"name": "Berkshire Hathaway", "ticker": "BRK-B", "weight": 1.0},
        ],
    },
}


def _determine_archetype(name: str, symbol: str) -> str:
    """Classify a fund or ETF by analyzing its name and symbol keywords."""
    combined = f"{name} {symbol}".lower()

    if any(k in combined for k in ["tech", "semiconductor", "semi", "nasdaq", "qqq", "software", "cloud", "cyber", "ai", "artificial"]):
        return "tech"
    if any(k in combined for k in ["s&p", "sp500", "us 500", "usa", "united states", "america"]):
        return "sp500"
    if any(k in combined for k in ["santé", "health", "pharma", "biotech", "medical"]):
        return "health"
    if any(k in combined for k in ["immo", "reit", "real estate", "selectiv"]):
        return "realestate"
    if any(k in combined for k in ["bond", "oblig", "treasury", "yield", "emprunt", "gilt", "bund"]):
        return "bonds"
    if any(k in combined for k in ["emerg", "asia", "asie", "china", "chine", "india", "inde", "bric"]):
        return "emerging"
    if any(k in combined for k in ["europe", "stoxx", "euro", "dax", "cac", "ftse"]):
        return "europe"
    if any(k in combined for k in ["flexible", "equilibre", "patrimoine", "long terme", "multi", "diversif", "allocation"]):
        return "multi_asset"
    
    return "world"


async def fetch_online_etf_details(symbol: str) -> Dict[str, Any]:
    """Fetch online metadata from Yahoo Finance search and chart endpoints."""
    cleaned = symbol.strip().upper()
    info = {
        "symbol": cleaned,
        "name": cleaned,
        "type": "ETF",
        "currency": "EUR",
        "isin": None,
    }

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=7.0) as client:
            # 1. Search endpoint
            search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={cleaned}&quotesCount=5&newsCount=0"
            s_resp = await client.get(search_url)
            if s_resp.status_code == 200:
                quotes = s_resp.json().get("quotes", [])
                for q in quotes:
                    if q.get("symbol", "").upper() == cleaned or cleaned.split(".")[0] in q.get("symbol", "").upper():
                        info["name"] = q.get("longname") or q.get("shortname") or info["name"]
                        info["type"] = q.get("quoteType") or info["type"]
                        break

            # 2. Chart endpoint for metadata
            chart_url = f"https://query2.finance.yahoo.com/v8/finance/chart/{cleaned}?interval=1d&range=1d"
            c_resp = await client.get(chart_url)
            if c_resp.status_code == 200:
                data = c_resp.json()
                res_list = data.get("chart", {}).get("result", [])
                if res_list:
                    meta = res_list[0].get("meta", {})
                    info["name"] = meta.get("shortName") or meta.get("longName") or info["name"]
                    info["currency"] = (meta.get("currency") or "EUR").upper()
                    if meta.get("instrumentType"):
                        info["type"] = meta.get("instrumentType")
    except Exception as e:
        logger.warning(f"Could not fetch online metadata for {cleaned}: {e}")

    return info


async def auto_decompose_and_create_profile(
    db: Session,
    symbol: str,
    name: Optional[str] = None,
    isin: Optional[str] = None
) -> Optional[EtfProfile]:
    """
    Search online to identify and decompose an unknown ETF or Fund,
    creating and saving a persistent EtfProfile in the database.
    """
    cleaned_sym = symbol.strip().upper()
    
    # 1. Check if already exists in DB
    existing = db.query(EtfProfile).filter(
        (EtfProfile.ticker.ilike(cleaned_sym)) |
        (EtfProfile.aliases.ilike(f'%"{cleaned_sym}"%'))
    ).first()
    if existing:
        return existing

    # 2. Fetch online metadata
    online_meta = await fetch_online_etf_details(cleaned_sym)
    fund_name = name or online_meta.get("name") or cleaned_sym
    fund_isin = isin or online_meta.get("isin")
    
    # 3. Determine archetype & composition
    archetype_key = _determine_archetype(fund_name, cleaned_sym)
    data = ARCHETYPES.get(archetype_key, ARCHETYPES["world"])

    aliases = [
        cleaned_sym,
        cleaned_sym.split(".")[0],
        fund_name.upper(),
    ]
    if fund_isin:
        aliases.append(fund_isin.upper())

    # 4. Create and persist profile
    try:
        profile = EtfProfile(
            name=fund_name,
            ticker=cleaned_sym,
            isin=fund_isin,
            aliases=json.dumps(aliases),
            countries=json.dumps(data["countries"]),
            sectors=json.dumps(data["sectors"]),
            top_holdings=json.dumps(data["top_holdings"]),
            is_system=False,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info(f"Auto-decomposed and created ETF profile: {profile.name} (#{profile.id}) based on '{archetype_key}'")

        # 5. Auto-link any existing portfolio holdings with this ticker
        db.query(PortfolioHolding).filter(
            PortfolioHolding.ticker.ilike(cleaned_sym),
            PortfolioHolding.etf_profile_id.is_(None)
        ).update({"etf_profile_id": profile.id}, synchronize_session=False)
        db.commit()

        return profile
    except Exception as e:
        db.rollback()
        logger.error(f"Error persisting auto-decomposed profile for {cleaned_sym}: {e}", exc_info=True)
        return None
