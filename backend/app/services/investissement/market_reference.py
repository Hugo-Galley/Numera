"""Référence de marché du scanner de diversification : l'ETF choisi (`market_reference_ticker`), sinon l'ETF
physique de référence du MSCI ACWI, créé et relu comme les références d'indice des synthétiques."""
from sqlalchemy.orm import Session

from app.db.system_settings import get_setting, set_setting
from app.domain.etf_profiles import match_profile
from app.domain.exposure.params import DEFAULT_MARKET_INDEX
from app.domain.holdings import normalize_ticker
from app.models.etf_profile import EtfProfile
from app.repositories.investissement import etf_profiles as repo
from app.services.investissement.etf_composition import ensure_index_reference

SETTING_KEY = "market_reference_ticker"


async def market_reference(db: Session) -> EtfProfile | None:
    """Profil ETF auquel la répartition du portefeuille est comparée ; None si aucune référence n'est connue."""
    ticker = get_setting(db, SETTING_KEY)
    if ticker:
        return match_profile(repo.all_profiles(db), str(ticker))
    return await ensure_index_reference(db, DEFAULT_MARKET_INDEX)


def set_market_reference(db: Session, ticker: str | None) -> dict[str, str | None]:
    """Enregistre la référence choisie (vide : retour au MSCI ACWI)."""
    value = normalize_ticker(ticker) if ticker and ticker.strip() else ""
    set_setting(db, SETTING_KEY, value)
    db.commit()
    return {"ticker": value or None}
