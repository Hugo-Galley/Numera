"""ISIN des positions, complété en tâche de fond depuis ce que l'application sait déjà.

Règle : un ISIN vide vaut mieux qu'un ISIN faux. Chaque source ne répond que si elle est sûre ; un ISIN
saisi (position non vide) n'est jamais modifié. Sources, dans l'ordre : opérations et inventaire du même
compte et du même ticker, profil ETF correspondant exactement, ISIN contenu dans le symbole, référentiel
des titres (ticker exact et place compatible), catalogues des émetteurs.
"""
import json
from collections.abc import Awaitable, Sequence
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.etf_profiles import isins_for_profiles
from app.domain.holdings import normalize_ticker
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


def _lookup_keys(symbol: str) -> set[str]:
    """Tickers du référentiel à lire pour ce symbole : le symbole entier (`BRK.B`) et sa base sans suffixe de place
    (`HO` pour `HO.PA`) ; `pick_isin` départage ensuite sur le ticker exact et la place."""
    upper = symbol.strip().upper()
    return {upper, upper.rsplit(".", 1)[0]}


def _securities_by_symbol(db: Session, symbols: list[str]) -> dict[str, list[IsinCandidate]]:
    tickers = set().union(*(_lookup_keys(s) for s in symbols))
    by_ticker: dict[str, list[IsinCandidate]] = {}
    for sec in securities_repo.by_tickers(db, tickers):
        by_ticker.setdefault(sec.ticker.upper(), []).append(IsinCandidate(sec.isin, sec.ticker, sec.exchange))
    return by_ticker


def _profile_isin(profiles: list[EtfProfile], symbol: str) -> str | None:
    """ISIN des profils dont le ticker ou un alias est exactement ce symbole ; None si aucun ou s'ils divergent."""
    wanted = normalize_ticker(symbol)
    isins: set[str] = set()
    for profile in profiles:
        try:
            names = {normalize_ticker(str(a)) for a in json.loads(profile.aliases)}
        except (ValueError, TypeError):
            names = set()
        if wanted == normalize_ticker(profile.ticker) or wanted in names:
            isins.add((profile.isin or "").upper().strip())
    valid = {i for i in isins if is_valid_isin(i)}
    return next(iter(valid)) if len(isins) == 1 and len(valid) == 1 else None


async def _from_catalogs(symbol: str, catalogs: Sequence[IsinCatalog]) -> str | None:
    for catalog in catalogs:
        try:
            isin = await catalog.find_isin_by_ticker(symbol)
        except Exception:
            logger.exception("Catalogue d'ISIN en échec pour %s", symbol)
            continue
        normalized = (isin or "").upper().strip()
        if is_valid_isin(normalized):
            return normalized
    return None


async def resolve_missing_isins(db: Session, catalogs: Sequence[IsinCatalog] | None = None, *, commit: bool = True,
                                account_id: int | None = None) -> int:
    """Complète l'ISIN des positions qui n'en ont pas ; renvoie leur nombre.

    Un seul commit, s'il y a du changement ; `commit=False` laisse la transaction à l'appelant (flush seulement) ;
    `account_id` limite aux positions d'un compte. Recopie ensuite les ISIN connus sur les profils ETF qui n'en ont
    pas (`copy_isins_to_profiles`)."""
    holdings = holdings_repo.holdings_without_isin(db, account_id)
    if not holdings:
        copy_isins_to_profiles(db, commit=commit)
        return 0
    recorded = _recorded_by_key(db)
    profiles = profiles_repo.all_profiles(db)
    candidates = _securities_by_symbol(db, [h.ticker for h in holdings])
    resolved = 0
    for holding in holdings:
        isin = await _resolve_one(holding, recorded, profiles, candidates, catalogs or ())
        if isin:
            holding.isin = isin
            resolved += 1
    if resolved:
        db.flush()
    copied = copy_isins_to_profiles(db, commit=False)  # l'ISIN trouvé sert aussi au profil ETF de la position
    if (resolved or copied) and commit:
        db.commit()
    return resolved


async def _resolve_one(holding: PortfolioHolding, recorded: dict[tuple[int, str], str], profiles: list[EtfProfile],
                       candidates: dict[str, list[IsinCandidate]], catalogs: Sequence[IsinCatalog]) -> str | None:
    symbol = holding.ticker
    isin = recorded.get((holding.account_id, normalize_ticker(symbol)))
    if isin:
        return isin
    # Le profil ne répond que si le ticker de la position est le sien ou un de ses alias : un rattachement
    # (`etf_profile_id`) hérité de l'ancien rapprochement par nom ne prouve rien.
    isin = _profile_isin(profiles, symbol)
    if isin:
        return isin
    isin = isin_from_symbol(symbol)
    if isin:
        return isin
    pool = [c for key in _lookup_keys(symbol) for c in candidates.get(key, [])]
    return pick_isin(symbol, pool) or await _from_catalogs(symbol, catalogs)


def copy_isins_to_profiles(db: Session, *, commit: bool = True) -> int:
    """Recopie l'ISIN, résolu ou saisi, des positions sur leur profil ETF qui n'en a pas (jamais en cas de doute) ;
    renvoie le nombre de profils complétés. Trois requêtes, quel que soit le nombre de profils."""
    isins = isins_for_profiles(profiles_repo.identities(db), profiles_repo.holding_isins(db))
    if isins:
        profiles_repo.set_isins(db, isins)
        if commit:
            db.commit()
        else:
            db.flush()
        logger.info(f"ISIN recopié sur {len(isins)} profil(s) ETF")
    return len(isins)
