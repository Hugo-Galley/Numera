"""Interface commune des émetteurs d'ETF et accès HTTP partagé (aucune écriture en base ni règle métier).

Les poids sont toujours en pourcentage (0–100), les pays en ISO 3166-1 alpha-3, les secteurs en libellés
français de l'application. Seuls des identifiants publics (ISIN, référence de fonds) sont envoyés.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Generic, Protocol, TypeVar

import httpx

from app.core.circuit_breaker import CircuitBreaker
from app.core.time import utcnow_naive

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
TIMEOUT = 30.0
CATALOG_TTL = timedelta(hours=24)
CATALOG_RETRY_AFTER = timedelta(minutes=10)

ClientFactory = Callable[[], httpx.AsyncClient]
T = TypeVar("T")


@dataclass(frozen=True)
class ProviderFund:
    provider: str  # "ishares" | "amundi" | "spdr" | "justetf"
    ref: str  # identifiant interne (productId iShares, ISIN Amundi, URL SPDR…)
    isin: str
    name: str
    ticker: str | None
    replication: str  # "physical" | "synthetic" | "unknown"
    index_name: str | None


@dataclass(frozen=True)
class Constituent:
    isin: str | None
    ticker: str | None
    name: str
    weight: float  # % 0-100
    country: str | None
    sector: str
    asset_class: str
    exchange: str | None


@dataclass(frozen=True)
class Composition:
    as_of: date
    lines: list[Constituent]  # vide pour justETF
    countries: dict[str, float] | None = None  # agrégats fournis tels quels (justETF)
    sectors: dict[str, float] | None = None
    top_holdings: list[dict[str, Any]] | None = None


class ProviderUnavailable(Exception):
    """Émetteur injoignable ou réponse inexploitable (différent de « fonds inconnu »)."""


class FundCompositionMissing(ProviderUnavailable):
    """L'émetteur répond, mais ne publie rien pour ce fonds (page 404, composition sans ligne) : lui n'est pas en panne."""


class Provider(Protocol):
    """Les trois méthodes sont des coroutines (typées `Awaitable` : une signature seule n'a rien à attendre)."""

    name: str

    def lookup(self, isin: str) -> Awaitable[ProviderFund | None]: ...

    def find_isin_by_ticker(self, symbol: str) -> Awaitable[str | None]: ...

    def fetch(self, fund: ProviderFund) -> Awaitable[Composition]: ...


def default_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, follow_redirects=True)


async def request(
    factory: ClientFactory, breaker: CircuitBreaker, method: str, url: str, **kwargs: Any
) -> httpx.Response:
    """Réponse 200 de l'émetteur, sinon `ProviderUnavailable` (`FundCompositionMissing` pour un 404).

    Le disjoncteur de l'émetteur compte les pannes (réseau, blocage, erreur serveur) ; un 404 n'en est pas une."""
    if not breaker.allow():
        raise ProviderUnavailable(f"{url} : émetteur en pause après des échecs répétés")
    try:
        async with factory() as client:
            response = await client.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        breaker.failure()
        raise ProviderUnavailable(f"{url} : {exc!r}") from exc
    if response.status_code == 404:
        raise FundCompositionMissing(f"{url} : HTTP 404")
    if response.status_code != 200:
        breaker.failure()
        raise ProviderUnavailable(f"{url} : HTTP {response.status_code}")
    breaker.success()
    return response


def read_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ProviderUnavailable(f"{response.request.url} : réponse illisible") from exc
    if not isinstance(payload, dict):
        raise ProviderUnavailable(f"{response.request.url} : format inattendu")
    return payload


def text_or_none(value: object) -> str | None:
    """Texte nettoyé ; les marqueurs d'absence des émetteurs (« - », « Unassigned ») valent `None`."""
    cleaned = str(value or "").strip()
    return None if cleaned in ("", "-", "Unassigned") else cleaned


class CatalogCache(Generic[T]):
    """Catalogue d'un émetteur, par ISIN, gardé 24 h en mémoire ; après un échec, pas de nouvelle tentative avant 10 min."""

    def __init__(self, load: Callable[[], Awaitable[dict[str, T]]]) -> None:
        self._load = load
        self._funds: dict[str, T] = {}
        self._expires_at: datetime | None = None
        self._retry_at: datetime | None = None

    async def get(self) -> dict[str, T]:
        now = utcnow_naive()
        if self._expires_at and now < self._expires_at:
            return self._funds
        if self._retry_at and now < self._retry_at:
            raise ProviderUnavailable("catalogue indisponible, nouvelle tentative plus tard")
        try:
            funds = await self._load()
            if not funds:
                raise ProviderUnavailable("catalogue sans aucun fonds")
        except ProviderUnavailable as exc:
            self._retry_at = now + CATALOG_RETRY_AFTER
            if isinstance(exc, FundCompositionMissing):  # catalogue introuvable : c'est l'émetteur qui fait défaut
                raise ProviderUnavailable(str(exc)) from exc
            raise
        self._funds, self._expires_at, self._retry_at = funds, now + CATALOG_TTL, None
        return funds
