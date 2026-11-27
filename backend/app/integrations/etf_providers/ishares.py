"""iShares : catalogue des fonds (site britannique) et composition complète publiée chaque jour."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.core.circuit_breaker import CircuitBreaker
from app.domain.etf_normalize import country_code, sector_label
from app.domain.isin import exchange_of
from app.integrations.etf_providers.base import (
    CatalogCache,
    ClientFactory,
    Composition,
    Constituent,
    ProviderFund,
    ProviderUnavailable,
    default_client,
    read_json,
    request,
    text_or_none,
)

_SITE = "https://www.ishares.com/varnish-api"
CATALOG_URL = f"{_SITE}/blk-product-screener-server/api/v1/product-screener/product-data"
CATALOG_PARAMS = {"country": "gb", "language": "en", "siteName": "ishares-uk", "userType": "individual"}
HOLDINGS_URL = f"{_SITE}/uk-retail01-product-data/product-data/api/v2/get-product-data"
HOLDINGS_PARAMS = {
    "appSubType": "ISHARES", "appType": "PRODUCT_PAGE", "component": "holdings.all", "locale": "en_GB",
    "targetSite": "ishares-uk", "userType": "individual", "excludeContent": "true", "includeConfig": "true",
}
_breaker = CircuitBreaker(cooldown=timedelta(minutes=10))


class IShares:
    name = "ishares"

    def __init__(self, client_factory: ClientFactory | None = None) -> None:
        self._client_factory = client_factory or default_client
        self._catalog = CatalogCache(self._load_catalog)

    async def lookup(self, isin: str) -> ProviderFund | None:
        return (await self._catalog.get()).get(isin.strip().upper())

    async def find_isin_by_ticker(self, symbol: str) -> str | None:
        """Le catalogue ne donne que le ticker de cotation à Londres : seul un symbole `.L` est comparable."""
        if exchange_of(symbol) != "LON":
            return None
        ticker = symbol.rsplit(".", 1)[0].strip().upper()
        found = [f.isin for f in (await self._catalog.get()).values() if (f.ticker or "").upper() == ticker]
        return found[0] if len(found) == 1 else None

    async def fetch(self, fund: ProviderFund) -> Composition:
        params = {**HOLDINGS_PARAMS, "portfolioId": fund.ref}
        response = await request(self._client_factory, _breaker, "GET", HOLDINGS_URL, params=params)
        return _parse_holdings(read_json(response))

    async def _load_catalog(self) -> dict[str, ProviderFund]:
        response = await request(self._client_factory, _breaker, "GET", CATALOG_URL, params=CATALOG_PARAMS)
        return _parse_catalog(read_json(response))


def _parse_catalog(payload: dict[str, Any]) -> dict[str, ProviderFund]:
    funds: dict[str, ProviderFund] = {}
    for product_id, product in payload.items():
        if not isinstance(product, dict):
            continue
        isin = text_or_none(product.get("isin"))
        name = " ".join(str(product.get("fundName") or "").split())
        if not isin or not name:
            continue
        replication = "synthetic" if "swap" in name.lower().split() else "physical"
        funds[isin] = ProviderFund(
            provider="ishares", ref=str(product_id), isin=isin, name=name,
            ticker=text_or_none(product.get("localExchangeTicker")), replication=replication, index_name=None,
        )
    return funds


def _parse_holdings(payload: dict[str, Any]) -> Composition:
    """La réponse est rangée par colonnes : une liste de valeurs par champ, de même longueur."""
    try:
        points = payload["componentsByNameMap"]["holdings"]["containersByNameMap"]["all"]["dataPointsByNameMap"]
        as_of = datetime.strptime(str(points["asOfDate"]["value"]), "%Y%m%d").date()
        columns = {name: points[name]["value"] for name in ("issueName", "holdingPercent", "assetClass")}
        size = len(columns["issueName"])
        for name in ("isin", "ticker", "countryOfRisk", "sectorName", "exchange"):
            columns[name] = points[name]["value"] if name in points else [None] * size
        if any(len(values) != size for values in columns.values()):
            raise ProviderUnavailable("composition iShares : colonnes de longueurs différentes")
        rows = [dict(zip(columns, values, strict=True)) for values in zip(*columns.values(), strict=True)]
        lines = [_line(row) for row in rows if isinstance(row["holdingPercent"], int | float)]
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderUnavailable("composition iShares : format inattendu") from exc
    return _composition(as_of, lines)


def _composition(as_of: date, lines: list[Constituent]) -> Composition:
    if not lines:
        raise ProviderUnavailable("composition iShares sans aucune ligne")
    return Composition(as_of=as_of, lines=lines)


def _line(row: dict[str, Any]) -> Constituent:
    return Constituent(
        isin=text_or_none(row["isin"]), ticker=text_or_none(row["ticker"]),
        name=str(row["issueName"] or "").strip(), weight=float(row["holdingPercent"]),
        country=country_code(row["countryOfRisk"]), sector=sector_label(row["sectorName"]),
        asset_class=str(row["assetClass"] or "").strip(), exchange=text_or_none(row["exchange"]),
    )
