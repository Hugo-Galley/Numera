"""Résolution stricte d'un ISIN depuis un ticker (sans base ni réseau).

Règle : un ISIN vide vaut mieux qu'un ISIN faux. Un candidat n'est retenu que si son ticker
est celui du symbole (suffixe de place retiré) ET si sa place est compatible avec le suffixe du symbole ;
ISRG.PA (un ETF coté à Paris) ne doit jamais résoudre vers l'ISIN américain d'Intuitive Surgical.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

# Suffixe Yahoo -> place.
_SUFFIX_TO_PLACE = {
    "PA": "PAR", "AS": "AMS", "BR": "BRU", "LS": "LIS", "MC": "MAD",
    "DE": "GER", "F": "GER", "SG": "GER", "L": "LON", "MI": "MIL", "SW": "SWX", "TO": "TOR",
    "T": "TYO", "HK": "HKG", "AX": "ASX", "ST": "STO", "CO": "CPH", "HE": "HEL",
    "OL": "OSL", "VI": "VIE", "IR": "DUB", "TA": "TLV", "SI": "SGX",
}

# Place -> mots-clés (minuscules) du nom de place donné par le fournisseur. "US" est traité à part.
_PLACE_KEYWORDS = {
    "PAR": ("paris",), "AMS": ("amsterdam",), "BRU": ("brussels",), "LIS": ("lisbon",),
    "MAD": ("madrid",), "GER": ("xetra", "frankfurt", "deutsche boerse", "stuttgart", "tradegate", "berlin"),
    "LON": ("london",), "MIL": ("borsa italiana", "milan"), "SWX": ("swiss",), "TOR": ("toronto",),
    "TYO": ("tokyo",), "HKG": ("hong kong",), "ASX": ("asx", "australia"),
    "HEL": ("helsinki",), "CPH": ("copenhagen",), "STO": ("stockholm",),
    "OSL": ("oslo",), "VIE": ("wiener", "vienna"), "DUB": ("irish", "dublin"),
    "TLV": ("tel aviv",), "SGX": ("singapore",),
}

# Place -> préfixes de pays ISIN, quand le fournisseur ne donne pas la place.
_PLACE_ISIN_PREFIXES = {
    "US": ("US", "CA"), "PAR": ("FR",), "AMS": ("NL",), "BRU": ("BE",), "LIS": ("PT",), "MAD": ("ES",),
    "GER": ("DE",), "LON": ("GB",), "MIL": ("IT",), "SWX": ("CH",), "TOR": ("CA",), "TYO": ("JP",),
    "HKG": ("HK",), "ASX": ("AU",), "HEL": ("FI",), "CPH": ("DK",), "STO": ("SE",), "OSL": ("NO",), "VIE": ("AT",),
    "DUB": ("IE",), "TLV": ("IL",), "SGX": ("SG",),
}


@dataclass(frozen=True)
class IsinCandidate:
    isin: str
    ticker: str
    exchange: str | None


def is_valid_isin(value: str) -> bool:
    """Format ISO 6166 et clé de contrôle (Luhn sur les chiffres obtenus en développant les lettres)."""
    if not _ISIN_RE.fullmatch(value):
        return False
    digits = "".join(str(int(c, 36)) for c in value)
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def isin_from_symbol(symbol: str) -> str | None:
    """`IE0002XZSHO1.SG` -> `IE0002XZSHO1` ; un symbole qui n'est pas un ISIN valide -> None."""
    base = symbol.split(".")[0].strip().upper()
    return base if is_valid_isin(base) else None


def _split(symbol: str) -> tuple[str, str | None]:
    """(ticker sans suffixe de place, place). `BRK.B` (classe d'actions d'une lettre inconnue) reste US."""
    if "." not in symbol:
        return symbol.strip().upper(), "US"
    base, suffix = symbol.rsplit(".", 1)
    suffix = suffix.strip().upper()
    if suffix in _SUFFIX_TO_PLACE:
        return base.strip().upper(), _SUFFIX_TO_PLACE[suffix]
    if len(suffix) == 1:
        return symbol.strip().upper(), "US"
    return base.strip().upper(), None


def exchange_of(symbol: str) -> str | None:
    """Place déduite du suffixe Yahoo ; sans suffixe : `US` ; suffixe inconnu : None."""
    return _split(symbol)[1]


_NORDIC_CITIES = ("helsinki", "copenhagen", "stockholm", "oslo", "iceland", "riga", "tallinn", "vilnius")


def _is_us_exchange(exchange: str) -> bool:
    """Liste blanche : toute autre place Nasdaq/Cboe (Stockholm, Dubai, Europe…) n'est pas américaine."""
    name = exchange.lower().strip()
    if "euronext" in name or "arca europe" in name:
        return False
    return (
        name in ("nasdaq", "nasdaq stock market")
        or name.startswith(("nasdaq global", "new york stock exchange", "cboe bzx"))
        or "nyse" in name
    )


def _is_compatible(place: str, candidate: IsinCandidate) -> bool:
    exchange = (candidate.exchange or "").strip()
    if not exchange:
        return candidate.isin[:2] in _PLACE_ISIN_PREFIXES.get(place, ())
    if place == "US":
        return _is_us_exchange(exchange)
    name = exchange.lower()
    if any(key in name for key in _PLACE_KEYWORDS.get(place, ())):
        return True
    # Place nordique générique (sans ville) : le pays de l'ISIN départage.
    generic = ("nordic" in name or "omx" in name) and not any(city in name for city in _NORDIC_CITIES)
    return place in ("HEL", "CPH", "STO") and generic and candidate.isin[:2] in _PLACE_ISIN_PREFIXES[place]


def pick_isin(symbol: str, candidates: list[IsinCandidate]) -> str | None:
    """ISIN du seul candidat de ticker exact et de place compatible ; None si aucun ou ambigu."""
    ticker, place = _split(symbol)
    if place is None or not ticker:
        return None
    isins = {
        c.isin
        for c in candidates
        if is_valid_isin(c.isin) and c.ticker.strip().upper() == ticker and _is_compatible(place, c)
    }
    return next(iter(isins)) if len(isins) == 1 else None
