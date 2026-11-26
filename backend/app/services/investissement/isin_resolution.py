"""ISIN des positions, complété en tâche de fond depuis ce que l'application sait déjà.

Règle : un ISIN vide vaut mieux qu'un ISIN faux. Chaque source ne répond que si elle est sûre ; un ISIN
saisi (position non vide) n'est jamais modifié. Sources, dans l'ordre : opérations et inventaire du même
compte et du même ticker, profil ETF correspondant exactement, ISIN contenu dans le symbole, référentiel
des titres (ticker exact et place compatible), catalogues des émetteurs.
"""
from collections.abc import Awaitable, Sequence
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.holdings import holding_profile, normalize_ticker
from app.domain.isin import IsinCandidate, is_valid_isin, isin_from_symbol, pick_isin
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.repositories.investissement import etf_profiles as profiles_repo
from app.repositories.investissement import holdings as holdings_repo
from app.repositories.investissement import securities as securities_repo

logger = get_logger(__name__)


class IsinCatalog(Protocol):
    """Catalogue d'un émetteur (iShares, Amundi) : ISIN d'un symbole Yahoo, ou None si inconnu."""

    def find_isin_by_ticker(self, symbol: str) -> Awaitable[str | None]: ...


def _recorded_by_key(db: Session) -> dict[tuple[int, str], str]:
    """ISIN saisi par (compte, ticker) ; ignoré si les lignes ne s'accordent pas sur un seul ISIN valide."""
    found: dict[tuple[int, str], set[str]] = {}
    for account_id, ticker, isin in holdings_repo.recorded_isins(db):
        found.setdefault((account_id, normalize_ticker(ticker)), set()).add(isin.upper().strip())
    return {k: next(iter(v)) for k, v in found.items() if len(v) == 1 and is_valid_isin(next(iter(v)))}


def _securities_by_symbol(db: Session, symbols: list[str]) -> dict[str, list[IsinCandidate]]:
    tickers = {s.split(".")[0].upper() for s in symbols}
    by_ticker: dict[str, list[IsinCandidate]] = {}
    for sec in securities_repo.by_tickers(db, tickers):
        by_ticker.setdefault(sec.ticker.upper(), []).append(IsinCandidate(sec.isin, sec.ticker, sec.exchange))
    return by_ticker


async def _from_catalogs(symbol: str, catalogs: Sequence[IsinCatalog]) -> str | None:
    for catalog in catalogs:
        try:
            isin = await catalog.find_isin_by_ticker(symbol)
        except Exception:
            logger.exception("Catalogue d'ISIN en échec pour %s", symbol)
            continue
        if isin and is_valid_isin(isin.upper().strip()):
            return isin.upper().strip()
    return None


async def resolve_missing_isins(db: Session, catalogs: Sequence[IsinCatalog] | None = None, *, commit: bool = True) -> int:
    """Complète l'ISIN des positions qui n'en ont pas ; renvoie leur nombre.

    Un seul commit, s'il y a du changement ; `commit=False` laisse la transaction à l'appelant (flush seulement)."""
    holdings = holdings_repo.holdings_without_isin(db)
    if not holdings:
        return 0
    recorded = _recorded_by_key(db)
    profiles = profiles_repo.all_profiles(db)
    # Un symbole sans suffixe de place ni point (AAPL) ou avec (HO.PA) : le référentiel est indexé sans suffixe,
    # `pick_isin` revérifie ticker et place ; BRK.B garde son point côté `pick_isin`.
    candidates = _securities_by_symbol(db, [h.ticker for h in holdings])
    resolved = 0
    for holding in holdings:
        isin = await _resolve_one(holding, recorded, profiles, candidates, catalogs or ())
        if isin:
            holding.isin = isin
            resolved += 1
    if resolved:
        db.commit() if commit else db.flush()
    return resolved


async def _resolve_one(holding: PortfolioHolding, recorded: dict[tuple[int, str], str], profiles: list[EtfProfile],
                       candidates: dict[str, list[IsinCandidate]], catalogs: Sequence[IsinCatalog]) -> str | None:
    symbol = holding.ticker
    isin = recorded.get((holding.account_id, normalize_ticker(symbol)))
    if isin:
        return isin
    profile = holding_profile(profiles, holding.etf_profile_id, symbol, None)
    if profile and profile.isin and is_valid_isin(profile.isin.upper().strip()):
        return profile.isin.upper().strip()
    isin = isin_from_symbol(symbol)
    if isin:
        return isin
    isin = pick_isin(symbol, candidates.get(symbol.split(".")[0].upper(), []))
    return isin or await _from_catalogs(symbol, catalogs)
