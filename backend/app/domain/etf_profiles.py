"""Profils ETF : correspondance d'un titre avec un profil connu (ticker, ISIN, alias, nom)."""
import json
from typing import List, Optional

from app.models.etf_profile import EtfProfile


def match_profile(profiles: List[EtfProfile], symbol: str, isin: Optional[str] = None, name: Optional[str] = None) -> Optional[EtfProfile]:
    """Find matching EtfProfile by ticker, isin or alias."""
    norm_symbol = symbol.upper().strip()
    norm_isin = (isin or "").upper().strip()
    norm_name = (name or "").lower().strip()

    # Exact isin or ticker match
    for p in profiles:
        if norm_isin and p.isin and p.isin.upper() == norm_isin:
            return p
        if p.ticker.upper() == norm_symbol:
            return p

        # Check aliases
        try:
            aliases = json.loads(p.aliases)
            for alias in aliases:
                if alias.upper() in (norm_symbol, norm_symbol.split(".")[0], norm_isin):
                    return p
        except Exception:
            pass

    # Name-based heuristic : nom vide => aucune correspondance (sinon "" est contenu dans tout),
    # et on exige que le nom complet du profil figure dans le libellé (pas l'inverse, trop large)
    if not norm_name:
        return None
    for p in profiles:
        p_name = p.name.lower().strip()
        if len(p_name) >= 6 and (p_name == norm_name or p_name in norm_name):
            return p

    return None


def profile_matches_query(p: EtfProfile, q_lower: str) -> bool:
    """Vrai si la recherche (en minuscules) vise ce profil : nom, ticker, ISIN ou alias."""
    p_name = p.name.lower()
    p_ticker = p.ticker.lower()
    p_isin = (p.isin or "").lower()

    matches = (
        q_lower in p_name
        or q_lower == p_ticker
        or q_lower in p_ticker
        or (p_isin and q_lower == p_isin)
    )
    if not matches:
        try:
            aliases = [a.lower() for a in json.loads(p.aliases)]
            if any(q_lower in a or a in q_lower for a in aliases):
                matches = True
        except Exception:
            pass
    return bool(matches)
