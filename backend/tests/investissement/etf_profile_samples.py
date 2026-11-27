"""Profils ETF d'exemple pour les tests : l'application n'en livre aucun."""
import json

from app.models.etf_profile import EtfProfile

_SAMPLES = (
    ("MSCI World", "CW8.PA", "LU1681043599", ["CW8", "CW8.PA", "FR0010315770"]),
    ("S&P 500", "ESE.PA", "FR0011550185", ["ESE", "ESE.PA"]),
    ("CAC 40", "C40.PA", "FR0007054316", ["C40", "C40.PA"]),
)


def add_sample_profiles(db) -> None:
    db.add_all([
        EtfProfile(name=name, ticker=ticker, isin=isin, aliases=json.dumps(aliases))
        for name, ticker, isin, aliases in _SAMPLES
    ])
    db.commit()
