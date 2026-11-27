"""justETF, source de repli : la page d'un fonds donne ses dix premiers pays, secteurs et lignes (pas la composition).

La page ne détaille pas les lignes : seuls des agrégats sont rendus, la part « Autre » restant non couverte.
"""
from __future__ import annotations

import asyncio
import html
import re
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta
from typing import Any

from app.core.circuit_breaker import CircuitBreaker
from app.domain.etf_normalize import UNKNOWN_LABEL, country_code, index_for_fund_name, sector_label
from app.domain.isin import is_valid_isin
from app.integrations.etf_providers.base import (
    ClientFactory,
    Composition,
    ProviderFund,
    ProviderUnavailable,
    default_client,
    request,
)

PAGE_URL = "https://www.justetf.com/fr/etf-profile.html"
_TABLES = ("countries", "sectors", "top-holdings")
_NAME = re.compile(r'data-testid="etf-holdings_description"[^>]*>[^<]*?composition (?:du |de la |de l[’\']|de )([^<]+?)\.?\s*<')
_PERCENT = re.compile(r'_percentage">\s*([0-9]+(?:,[0-9]+)?)\s*%')
_LABEL = re.compile(r'_value_name">([^<]+)<')
_REPLICATION = re.compile(r'data-testid="etf-profile-header_replication-value"[^>]*>\s*([^<]+?)\s*<')
_REPLICATIONS = {"Physique": "physical", "Synthétique": "synthetic"}
_AS_OF = re.compile(r'data-testid="tl_etf-holdings_reference-date"[^>]*>[^<0-9]*([0-9]{2}/[0-9]{2}/[0-9]{4})\s*<')
_HOLDING = re.compile(r'href="[^"]*/stock-profiles/([A-Z0-9]{12})"[^>]*title="([^"]+)"')

_breaker = CircuitBreaker(cooldown=timedelta(minutes=10))


class JustEtf:
    name = "justetf"

    def __init__(self, client_factory: ClientFactory | None = None) -> None:
        self._client_factory = client_factory or default_client

    async def lookup(self, isin: str) -> ProviderFund | None:
        """None si la page ne montre aucune composition (fonds inconnu ou sans détail)."""
        wanted = isin.strip().upper()
        if not is_valid_isin(wanted):
            return None
        page = await self._page(wanted)
        if not any(_rows(page, table) for table in _TABLES):
            return None
        found = _NAME.search(page)
        name = html.unescape(found.group(1)).strip() if found else wanted
        stated = _REPLICATION.search(page)
        replication = _REPLICATIONS.get(html.unescape(stated.group(1)), "unknown") if stated else "unknown"
        return ProviderFund(
            provider="justetf", ref=wanted, isin=wanted, name=name, ticker=None,
            replication=replication, index_name=index_for_fund_name(name),
        )

    def find_isin_by_ticker(self, symbol: str) -> Awaitable[str | None]:
        """Pas de catalogue : aucun ISIN n'est déduit d'un ticker."""
        return asyncio.sleep(0, None)

    async def fetch(self, fund: ProviderFund) -> Composition:
        """La date est celle que publie la page (« État : jj/mm/aaaa ») ; sans elle, aucune."""
        page = await self._page(fund.ref)
        countries = _breakdown(_rows(page, "countries"), country_code)
        sectors = _breakdown(_rows(page, "sectors"), _known_sector)
        top_holdings = _top_holdings(_rows(page, "top-holdings"))
        if not (countries or sectors or top_holdings):
            raise ProviderUnavailable(f"page justETF sans composition lisible pour {fund.isin}")
        return Composition(
            as_of=_published_date(page), lines=[], countries=countries, sectors=sectors, top_holdings=top_holdings
        )

    async def _page(self, isin: str) -> str:
        response = await request(self._client_factory, _breaker, "GET", PAGE_URL, params={"isin": isin})
        return response.text


def _published_date(page: str) -> date | None:
    found = _AS_OF.search(page)
    try:
        return datetime.strptime(found.group(1), "%d/%m/%Y").date() if found else None
    except ValueError:
        return None


def _rows(page: str, table: str) -> list[str]:
    return re.findall(rf'<tr data-testid="etf-holdings_{table}_row">(.*?)</tr>', page, re.DOTALL)


def _weight(row: str) -> float | None:
    found = _PERCENT.search(row)
    return float(found.group(1).replace(",", ".")) if found else None


def _known_sector(label: str) -> str | None:
    sector = sector_label(label)
    return None if sector == UNKNOWN_LABEL else sector


def _breakdown(rows: list[str], normalize: Callable[[str], str | None]) -> dict[str, float]:
    """Poids par clé normalisée ; un libellé inconnu (« Autre ») est ignoré."""
    result: dict[str, float] = {}
    for row in rows:
        label, weight = _LABEL.search(row), _weight(row)
        key = normalize(html.unescape(label.group(1)).strip()) if label else None
        if key and weight:
            result[key] = round(result.get(key, 0.0) + weight, 2)
    return result


def _top_holdings(rows: list[str]) -> list[dict[str, Any]]:
    holdings: list[dict[str, Any]] = []
    for row in rows:
        found, weight = _HOLDING.search(row), _weight(row)
        if found and weight:
            isin = found.group(1)
            holdings.append({
                "name": html.unescape(found.group(2)), "ticker": None,
                "isin": isin if is_valid_isin(isin) else None, "weight": weight,
            })
    return holdings
