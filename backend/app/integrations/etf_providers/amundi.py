"""Amundi : fiche et composition complète d'un fonds par ISIN, et catalogue de ses cotations (API JSON publique,
sans clé).

Les poids sont publiés en fractions (0–1). La place d'une ligne comme d'une cotation est déduite de son code
Bloomberg (« AAPL UW », « ISRG FP »), avec des noms que la résolution d'ISIN (`domain/isin`) sait comparer.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.core.circuit_breaker import CircuitBreaker
from app.domain.etf_normalize import country_code, index_for_fund_name, sector_label
from app.domain.isin import IsinCandidate, is_valid_isin, pick_isin
from app.integrations.etf_providers.base import (
    CatalogCache,
    ClientFactory,
    Composition,
    Constituent,
    FundCompositionMissing,
    ProviderFund,
    ProviderUnavailable,
    default_client,
    read_json,
    request,
    text_or_none,
)

PRODUCTS_URL = "https://www.amundietf.fr/mapi/ProductAPI/getProductsData"
_CONTEXT = {"countryCode": "FRA", "languageCode": "en", "userProfileName": "RETAIL"}
_CHARACTERISTICS = ["SHARE_MARKETING_NAME", "MNEMO", "FUND_REPLICATION_METHODOLOGY"]
_COMPOSITION_FIELDS = ["date", "type", "bbg", "isin", "name", "weight", "sector", "countryOfRisk"]
_REPLICATIONS = {"Direct(Physical)": "physical", "Indirect(Swap Based)": "synthetic"}

# Code de place Bloomberg -> nom de place
_BLOOMBERG_EXCHANGES = {
    **dict.fromkeys(("UW", "UQ", "UR"), "NASDAQ"),
    **dict.fromkeys(("UN", "US"), "New York Stock Exchange"),
    **dict.fromkeys(("CN", "CT"), "Toronto Stock Exchange"),
    **dict.fromkeys(("GY", "GR"), "Xetra"),
    **dict.fromkeys(("JT", "JP"), "Tokyo Stock Exchange"),
    **dict.fromkeys(("SE", "SW", "VX"), "SIX Swiss Exchange"),
    **dict.fromkeys(("SM", "SQ"), "Bolsa de Madrid"),
    **dict.fromkeys(("AT", "AU"), "ASX"),
    "FP": "Euronext Paris", "NA": "Euronext Amsterdam", "BB": "Euronext Brussels", "PL": "Euronext Lisbon",
    "LN": "London Stock Exchange", "IM": "Borsa Italiana", "FH": "Nasdaq Helsinki", "SS": "Nasdaq Stockholm",
    "DC": "Nasdaq Copenhagen", "NO": "Oslo Bors", "AV": "Wiener Boerse", "ID": "Irish Stock Exchange",
    "HK": "Hong Kong Stock Exchange", "IT": "Tel Aviv Stock Exchange", "SP": "Singapore Exchange",
}

_breaker = CircuitBreaker(cooldown=timedelta(minutes=10))


class Amundi:
    name = "amundi"

    def __init__(self, client_factory: ClientFactory | None = None) -> None:
        self._client_factory = client_factory or default_client
        self._catalog = CatalogCache(self._load_catalog)

    async def lookup(self, isin: str) -> ProviderFund | None:
        wanted = isin.strip().upper()
        product = await self._product(wanted, {"characteristics": _CHARACTERISTICS})
        if product is None:
            return None
        characteristics = product.get("characteristics") or {}
        name = text_or_none(characteristics.get("SHARE_MARKETING_NAME"))
        if not name:
            return None
        return ProviderFund(
            provider="amundi", ref=wanted, isin=wanted, name=name,
            ticker=text_or_none(characteristics.get("MNEMO")),
            replication=_REPLICATIONS.get(str(characteristics.get("FUND_REPLICATION_METHODOLOGY")), "unknown"),
            index_name=index_for_fund_name(name),
        )

    async def find_isin_by_ticker(self, symbol: str) -> str | None:
        """ISIN du seul fonds coté sous ce ticker exact sur la place du symbole (`ISRG.PA` -> « ISRG FP »)."""
        listings = (await self._catalog.get()).values()
        return pick_isin(symbol, [candidate for candidates in listings for candidate in candidates])

    async def _load_catalog(self) -> dict[str, list[IsinCandidate]]:
        """Sans `productIds`, l'API renvoie tous les produits."""
        products = await self._products({"characteristics": ["MNEMO", "LISTINGS"]})
        try:
            catalog = {str(p["productId"]): _listings(p) for p in products if "productId" in p}
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderUnavailable("catalogue Amundi : format inattendu") from exc
        return {isin: listings for isin, listings in catalog.items() if listings}

    async def fetch(self, fund: ProviderFund) -> Composition:
        product = await self._product(fund.ref, {"composition": {"compositionFields": _COMPOSITION_FIELDS}})
        try:
            rows = [entry["compositionCharacteristics"] for entry in product["composition"]["compositionData"]] if product else []
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderUnavailable(f"composition Amundi : format inattendu pour {fund.isin}") from exc
        if not rows:
            raise FundCompositionMissing(f"composition Amundi vide pour {fund.isin}")
        try:
            as_of = max(date.fromisoformat(str(row["date"])) for row in rows)
            lines = [_line(row) for row in rows]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ProviderUnavailable(f"composition Amundi : format inattendu pour {fund.isin}") from exc
        return Composition(as_of=as_of, lines=lines)

    async def _product(self, isin: str, wanted: dict[str, Any]) -> dict[str, Any] | None:
        products = await self._products({"productIds": [isin], **wanted})
        found: dict[str, Any] | None = next(
            (p for p in products if isinstance(p, dict) and p.get("productId") == isin), None)
        return found

    async def _products(self, wanted: dict[str, Any]) -> list[Any]:
        body = {"context": _CONTEXT, "productType": "PRODUCT", **wanted}
        response = await request(self._client_factory, _breaker, "POST", PRODUCTS_URL, json=body)
        products = read_json(response).get("products")
        if not isinstance(products, list):
            raise ProviderUnavailable("réponse Amundi sans liste de produits")
        return products


def _listings(product: dict[str, Any]) -> list[IsinCandidate]:
    isin = str(product["productId"])
    found = (_ticker_and_exchange(x.get("ticker")) for x in (product.get("characteristics") or {}).get("LISTINGS") or [])
    return [IsinCandidate(isin, ticker, exchange) for ticker, exchange in found if ticker]


def _ticker_and_exchange(bbg: object) -> tuple[str | None, str | None]:
    """« BRK/B UN » -> (`BRK.B`, `New York Stock Exchange`).

    Une place inconnue garde son code : sans place du tout, la résolution d'ISIN se rabattrait sur le pays de l'ISIN."""
    parts = str(bbg or "").split()
    if len(parts) < 2:
        return None, None
    ticker = " ".join(parts[:-1]).rstrip("/").replace("/", ".")
    return ticker or None, _BLOOMBERG_EXCHANGES.get(parts[-1], f"Bloomberg {parts[-1]}")


def _line(row: dict[str, Any]) -> Constituent:
    ticker, exchange = _ticker_and_exchange(row.get("bbg"))
    isin = str(row.get("isin") or "").strip().upper()
    return Constituent(
        isin=isin if is_valid_isin(isin) else None, ticker=ticker, name=str(row["name"]).strip(),
        weight=float(row["weight"]) * 100, country=country_code(row.get("countryOfRisk")),
        sector=sector_label(row.get("sector")), asset_class=str(row.get("type") or "").strip(), exchange=exchange,
    )
