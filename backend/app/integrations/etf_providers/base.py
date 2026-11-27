"""Interface commune des émetteurs d'ETF et accès HTTP partagé (aucune écriture en base ni règle métier).

Les poids sont toujours en pourcentage (0–100), les pays en ISO 3166-1 alpha-3, les secteurs en libellés
français de l'application. Seuls des identifiants publics (ISIN, référence de fonds) sont envoyés.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import httpx

from app.core.circuit_breaker import CircuitBreaker

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
TIMEOUT = 30.0

ClientFactory = Callable[[], httpx.AsyncClient]


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
    """Réponse 200 de l'émetteur, sinon `ProviderUnavailable`.

    Le disjoncteur de l'émetteur compte les pannes (réseau, blocage, erreur serveur) ; un 404 n'en est pas une."""
    if not breaker.allow():
        raise ProviderUnavailable(f"{url} : émetteur en pause après des échecs répétés")
    try:
        async with factory() as client:
            response = await client.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        breaker.failure()
        raise ProviderUnavailable(f"{url} : {exc!r}") from exc
    if response.status_code != 200:
        if response.status_code != 404:
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
