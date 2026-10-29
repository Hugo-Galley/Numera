"""Règles pures sur les cotations : devise d'un ticker Yahoo, cours en pence, conversion EUR, libellés d'actifs."""
import re
from typing import Dict, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Devise de cotation déduite du suffixe Yahoo (la recherche ne renvoie pas la devise)
QUOTE_SUFFIX_CURRENCIES: Dict[str, str] = {
    **{sfx: "EUR" for sfx in (".PA", ".AS", ".BR", ".DE", ".F", ".SG", ".MU", ".DU", ".HM", ".BE", ".MI", ".MC", ".VI", ".LS", ".HE", ".IR")},
    ".SW": "CHF",
    ".L": "GBP",
}


def guess_quote_currency(symbol: str) -> str:
    """Devise probable d'un ticker Yahoo (`CW8.PA` → EUR, `BTC-EUR` → EUR, `AAPL` → USD)."""
    sym = symbol.upper().strip()
    if "-" in sym and len(sym.rsplit("-", 1)[1]) == 3:
        return sym.rsplit("-", 1)[1]
    for suffix, currency in QUOTE_SUFFIX_CURRENCIES.items():
        if sym.endswith(suffix):
            return currency
    return "USD"


def normalize_price(price: float, raw_currency: str) -> tuple[float, str]:
    if raw_currency in ("GBp", "GBX"):
        # Cotations LSE en pence : on ramène en livres
        return float(price) / 100.0, "GBP"
    return float(price), (raw_currency or "EUR").upper()


def to_eur(price: float, currency: str, rates: Dict[str, float]) -> Optional[float]:
    rate = rates.get(currency)
    if not rate:
        logger.warning(f"No EUR exchange rate for {currency}: price left unconverted")
        return None
    return price / rate


def extract_asset_clean_name(note: str) -> Optional[str]:
    """Clean up transaction note to extract company or asset name."""
    if not note:
        return None
    cleaned = note.strip()

    # Remove common prefix words: "Achat ", "Dividende ", "Vente ", "Achat d'actions "
    cleaned = re.sub(r'^(achat d\'actions|achat actions|achat action|achat de|achat|dividende de|dividende|vente de|vente)\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\(.*\)', '', cleaned) # Remove parentheses
    cleaned = cleaned.strip()

    if len(cleaned) < 2:
        return None

    # Common mappings
    mapping = {
        "apple": "Apple",
        "total": "TotalEnergies",
        "total energie": "TotalEnergies",
        "totalenergies": "TotalEnergies",
        "microsoft": "Microsoft",
        "cisco": "Cisco",
        "blackrock": "BlackRock",
        "air liquide": "Air Liquide",
        "airliquide": "Air Liquide",
        "lvmh": "LVMH",
        "cw8": "Amundi MSCI World",
        "wpea": "iShares MSCI World Swap PEA",
        "ese": "BNP Paribas Easy S&P 500",
    }
    return mapping.get(cleaned.lower(), cleaned)
