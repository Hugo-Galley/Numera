import json
from sqlalchemy.orm import Session
from app.models.etf_profile import EtfProfile
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_ETF_PRESETS = [
    {
        "name": "MSCI World",
        "ticker": "CW8.PA",
        "isin": "LU1681043599",
        "aliases": ["CW8", "CW8.PA", "WPEA", "WPEA.PA", "EWLD", "EWLD.PA", "URTH", "IWDA", "SWDA", "LU1681043599", "IE0002XZSHO1", "FR0010315770", "AHYQ.DE"],
        "countries": {
            "USA": 71.2,
            "JPN": 5.3,
            "GBR": 3.7,
            "CAN": 3.1,
            "FRA": 2.8,
            "CHE": 2.4,
            "DEU": 2.1,
            "AUS": 1.8,
            "NLD": 1.3,
            "SWE": 0.8,
            "Autres": 5.5,
        },
        "sectors": {
            "Technologie": 25.1,
            "Finance": 15.2,
            "Santé": 11.8,
            "Consommation discrétionnaire": 10.4,
            "Industrie": 10.2,
            "Services de communication": 7.5,
            "Biens de consommation": 6.2,
            "Énergie": 4.1,
            "Matériaux": 3.6,
            "Services aux collectivités": 2.8,
            "Immobilier": 2.1,
            "Autres": 1.0,
        },
        "top_holdings": [
            {"name": "Apple", "ticker": "AAPL", "weight": 4.8},
            {"name": "Microsoft", "ticker": "MSFT", "weight": 4.3},
            {"name": "Nvidia", "ticker": "NVDA", "weight": 4.1},
            {"name": "Amazon", "ticker": "AMZN", "weight": 2.6},
            {"name": "Alphabet (Google)", "ticker": "GOOGL", "weight": 2.9},
            {"name": "Meta Platforms", "ticker": "META", "weight": 1.5},
            {"name": "Eli Lilly", "ticker": "LLY", "weight": 1.0},
            {"name": "Broadcom", "ticker": "AVGO", "weight": 0.9},
            {"name": "Tesla", "ticker": "TSLA", "weight": 0.9},
            {"name": "Berkshire Hathaway", "ticker": "BRK-B", "weight": 0.8},
            {"name": "JPMorgan Chase", "ticker": "JPM", "weight": 0.8},
        ],
    },
    {
        "name": "S&P 500",
        "ticker": "ESE.PA",
        "isin": "FR0011550185",
        "aliases": ["ESE", "ESE.PA", "PUST", "PUST.PA", "VOO", "SPY", "IVV", "CSPX", "FR0011550185", "IE00B5BMR087"],
        "countries": {
            "USA": 100.0,
        },
        "sectors": {
            "Technologie": 31.5,
            "Finance": 13.8,
            "Santé": 11.5,
            "Consommation discrétionnaire": 10.1,
            "Services de communication": 8.9,
            "Industrie": 8.4,
            "Biens de consommation": 5.8,
            "Énergie": 3.6,
            "Matériaux": 2.4,
            "Services aux collectivités": 2.2,
            "Immobilier": 1.8,
        },
        "top_holdings": [
            {"name": "Apple", "ticker": "AAPL", "weight": 7.1},
            {"name": "Microsoft", "ticker": "MSFT", "weight": 6.5},
            {"name": "Nvidia", "ticker": "NVDA", "weight": 6.1},
            {"name": "Amazon", "ticker": "AMZN", "weight": 3.8},
            {"name": "Alphabet (Google)", "ticker": "GOOGL", "weight": 4.3},
            {"name": "Meta Platforms", "ticker": "META", "weight": 2.4},
            {"name": "Berkshire Hathaway", "ticker": "BRK-B", "weight": 1.7},
            {"name": "Eli Lilly", "ticker": "LLY", "weight": 1.5},
            {"name": "Broadcom", "ticker": "AVGO", "weight": 1.4},
            {"name": "Tesla", "ticker": "TSLA", "weight": 1.2},
            {"name": "JPMorgan Chase", "ticker": "JPM", "weight": 1.3},
        ],
    },
    {
        "name": "CAC 40",
        "ticker": "C40.PA",
        "isin": "FR0007054316",
        "aliases": ["CAC40", "C40", "C40.PA", "LQQ", "LQQ.PA", "PX1", "FR0007054316", "FR0010592014"],
        "countries": {
            "FRA": 100.0,
        },
        "sectors": {
            "Consommation discrétionnaire": 26.5,
            "Industrie": 21.2,
            "Santé": 14.2,
            "Finance": 11.5,
            "Énergie": 9.1,
            "Matériaux": 7.8,
            "Technologie": 5.4,
            "Autres": 4.3,
        },
        "top_holdings": [
            {"name": "LVMH", "ticker": "MC.PA", "weight": 10.2},
            {"name": "TotalEnergies", "ticker": "TTE.PA", "weight": 8.4},
            {"name": "Schneider Electric", "ticker": "SU.PA", "weight": 7.8},
            {"name": "Sanofi", "ticker": "SAN.PA", "weight": 7.1},
            {"name": "Air Liquide", "ticker": "AI.PA", "weight": 6.9},
            {"name": "Hermès", "ticker": "RMS.PA", "weight": 5.8},
            {"name": "BNP Paribas", "ticker": "BNP.PA", "weight": 5.4},
            {"name": "Airbus", "ticker": "AIR.PA", "weight": 5.1},
            {"name": "L'Oréal", "ticker": "OR.PA", "weight": 4.9},
            {"name": "EssilorLuxottica", "ticker": "EL.PA", "weight": 4.2},
        ],
    },
    {
        "name": "Nasdaq 100",
        "ticker": "PANX.PA",
        "isin": "FR0011550193",
        "aliases": ["PANX", "PANX.PA", "UST", "UST.PA", "QQQ", "EQQQ", "FR0011550193"],
        "countries": {
            "USA": 98.2,
            "NLD": 1.8,
        },
        "sectors": {
            "Technologie": 51.2,
            "Services de communication": 15.4,
            "Consommation discrétionnaire": 13.1,
            "Santé": 6.4,
            "Biens de consommation": 4.2,
            "Industrie": 3.8,
            "Autres": 5.9,
        },
        "top_holdings": [
            {"name": "Apple", "ticker": "AAPL", "weight": 8.9},
            {"name": "Microsoft", "ticker": "MSFT", "weight": 8.1},
            {"name": "Nvidia", "ticker": "NVDA", "weight": 7.8},
            {"name": "Amazon", "ticker": "AMZN", "weight": 5.2},
            {"name": "Broadcom", "ticker": "AVGO", "weight": 4.6},
            {"name": "Meta Platforms", "ticker": "META", "weight": 4.3},
            {"name": "Alphabet (Google)", "ticker": "GOOGL", "weight": 5.5},
            {"name": "Tesla", "ticker": "TSLA", "weight": 2.6},
            {"name": "Costco", "ticker": "COST", "weight": 2.4},
        ],
    },
    {
        "name": "STOXX Europe 600",
        "ticker": "MEUD.PA",
        "isin": "FR0010791004",
        "aliases": ["MEUD", "MEUD.PA", "EXSA", "ETZ", "FR0010791004", "LU0908500753"],
        "countries": {
            "GBR": 22.5,
            "FRA": 17.8,
            "CHE": 14.2,
            "DEU": 13.5,
            "NLD": 7.2,
            "SWE": 5.4,
            "ITA": 4.3,
            "ESP": 4.1,
            "DNK": 3.8,
            "Autres": 7.2,
        },
        "sectors": {
            "Finance": 18.1,
            "Santé": 15.4,
            "Industrie": 14.8,
            "Consommation discrétionnaire": 10.2,
            "Biens de consommation": 9.8,
            "Technologie": 7.9,
            "Matériaux": 6.5,
            "Énergie": 5.8,
            "Services aux collectivités": 4.2,
            "Services de communication": 3.8,
            "Immobilier": 3.5,
        },
        "top_holdings": [
            {"name": "Novo Nordisk", "ticker": "NOVO-B.CO", "weight": 3.5},
            {"name": "ASML", "ticker": "ASML.AS", "weight": 3.1},
            {"name": "Nestlé", "ticker": "NESN.SW", "weight": 2.7},
            {"name": "SAP", "ticker": "SAP.DE", "weight": 2.2},
            {"name": "AstraZeneca", "ticker": "AZN.L", "weight": 2.1},
            {"name": "Shell", "ticker": "SHEL.L", "weight": 2.0},
            {"name": "Novartis", "ticker": "NOVN.SW", "weight": 1.9},
            {"name": "Roche", "ticker": "ROG.SW", "weight": 1.8},
            {"name": "LVMH", "ticker": "MC.PA", "weight": 1.7},
            {"name": "TotalEnergies", "ticker": "TTE.PA", "weight": 1.4},
        ],
    },
    {
        "name": "MSCI Emerging Markets",
        "ticker": "PAEEM.PA",
        "isin": "FR0013412020",
        "aliases": ["PAASI", "PAASI.PA", "PAEEM", "PAEEM.PA", "EEM", "VWO", "FR0013412020", "LU1681045370"],
        "countries": {
            "CHN": 24.8,
            "IND": 19.5,
            "TWN": 19.2,
            "KOR": 11.2,
            "BRA": 4.8,
            "SAU": 3.7,
            "ZAF": 2.8,
            "MEX": 2.4,
            "Autres": 11.6,
        },
        "sectors": {
            "Technologie": 24.2,
            "Finance": 22.8,
            "Consommation discrétionnaire": 12.5,
            "Services de communication": 9.1,
            "Matériaux": 7.2,
            "Énergie": 5.4,
            "Industrie": 5.1,
            "Biens de consommation": 4.8,
            "Santé": 3.5,
            "Autres": 5.4,
        },
        "top_holdings": [
            {"name": "TSMC (Taiwan Semiconductor)", "ticker": "TSM", "weight": 9.8},
            {"name": "Tencent", "ticker": "0700.HK", "weight": 4.3},
            {"name": "Samsung Electronics", "ticker": "005930.KS", "weight": 3.9},
            {"name": "Alibaba", "ticker": "BABA", "weight": 2.4},
            {"name": "Reliance Industries", "ticker": "RELIANCE.NS", "weight": 1.5},
            {"name": "Meituan", "ticker": "3690.HK", "weight": 1.2},
            {"name": "ICICI Bank", "ticker": "IBN", "weight": 1.1},
            {"name": "Infosys", "ticker": "INFY", "weight": 1.0},
            {"name": "SK Hynix", "ticker": "000660.KS", "weight": 0.9},
        ],
    },
]


def seed_etf_profiles(db: Session) -> None:
    """
    Seed or update system ETF profiles.
    """
    count = 0
    for preset in SYSTEM_ETF_PRESETS:
        existing = db.query(EtfProfile).filter(EtfProfile.name == preset["name"]).first()
        if not existing:
            profile = EtfProfile(
                name=preset["name"],
                ticker=preset["ticker"],
                isin=preset["isin"],
                aliases=json.dumps(preset["aliases"]),
                countries=json.dumps(preset["countries"]),
                sectors=json.dumps(preset["sectors"]),
                top_holdings=json.dumps(preset["top_holdings"]),
                is_system=True,
            )
            db.add(profile)
            count += 1
        else:
            # Update aliases and preset data if system
            if existing.is_system:
                existing.ticker = preset["ticker"]
                existing.isin = preset["isin"]
                existing.aliases = json.dumps(preset["aliases"])
                existing.countries = json.dumps(preset["countries"])
                existing.sectors = json.dumps(preset["sectors"])
                existing.top_holdings = json.dumps(preset["top_holdings"])
    
    if count > 0:
        db.commit()
        logger.info(f"Seeded {count} system ETF profiles.")
