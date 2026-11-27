"""SPDR (State Street) : catalogue du « fund finder » européen et composition quotidienne au format xlsx."""
from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable
from datetime import datetime, timedelta
from typing import Any

from app.core.circuit_breaker import CircuitBreaker
from app.domain.etf_normalize import country_code, index_for_fund_name, sector_label
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
from app.integrations.xlsx import read_rows

SITE = "https://www.ssga.com"
CATALOG_URL = f"{SITE}/bin/v1/ssmp/fund/fundfinder"
CATALOG_PARAMS = {"country": "fr", "language": "fr", "role": "intermediary", "product": "etfs", "ui": "fund-finder"}
_KID_ISIN = re.compile(r"[?&]isin=([A-Z]{2}[A-Z0-9]{9}[0-9])")
_NO_CLASS = "Cash and/or Derivatives"  # le fichier ne donne pas de classe d'actif : sans ISIN ni secteur, ce n'est pas une action

_breaker = CircuitBreaker(cooldown=timedelta(minutes=10))


class Spdr:
    name = "spdr"

    def __init__(self, client_factory: ClientFactory | None = None) -> None:
        self._client_factory = client_factory or default_client
        self._catalog = CatalogCache(self._load_catalog)

    async def lookup(self, isin: str) -> ProviderFund | None:
        return (await self._catalog.get()).get(isin.strip().upper())

    def find_isin_by_ticker(self, symbol: str) -> Awaitable[str | None]:
        """Le catalogue ne donne qu'une cotation par fonds, parfois en désaccord avec sa place : aucun ISIN n'en est déduit."""
        return asyncio.sleep(0, None)

    async def fetch(self, fund: ProviderFund) -> Composition:
        if not fund.ref.startswith(f"{SITE}/"):
            raise ProviderUnavailable(f"adresse SPDR inattendue : {fund.ref}")
        response = await request(self._client_factory, _breaker, "GET", fund.ref)
        try:
            return _parse_holdings(read_rows(response.content))
        except ValueError as exc:
            raise ProviderUnavailable(f"composition SPDR inexploitable pour {fund.isin} : {exc}") from exc

    async def _load_catalog(self) -> dict[str, ProviderFund]:
        response = await request(self._client_factory, _breaker, "GET", CATALOG_URL, params=CATALOG_PARAMS)
        try:
            rows = read_json(response)["data"]["funds"]["etfs"]["datas"]
            return {fund.isin: fund for row in rows if (fund := _fund(row))}
        except (KeyError, TypeError, AttributeError, IndexError) as exc:
            raise ProviderUnavailable("catalogue SPDR : format inattendu") from exc


def _fund(row: dict[str, Any]) -> ProviderFund | None:
    """L'ISIN n'a pas de champ propre : il figure dans le lien du document d'informations clés (KID)."""
    documents = {d["docType"]: str(d["docs"][0]["path"]) for d in row.get("documentPdf") or [] if d.get("docs")}
    isin = _KID_ISIN.search(documents.get("Kid", ""))
    path = documents.get("Holdings-daily", "")
    name = text_or_none(row.get("fundName"))
    if not (isin and name and path.startswith("/") and path.endswith(".xlsx")):
        return None
    ticker = str(row.get("fundTicker") or "").split()
    replication = "synthetic" if "swap" in name.lower().split() else "physical"
    return ProviderFund(
        provider="spdr", ref=f"{SITE}{path}", isin=isin.group(1), name=name,
        ticker=ticker[0] if ticker else None, replication=replication, index_name=index_for_fund_name(name),
    )


def _parse_holdings(rows: list[list[str]]) -> Composition:
    """En-tête (« Holdings As Of: »), puis un tableau terminé par la première ligne vide (mentions légales ensuite)."""
    header = next((i for i, row in enumerate(rows) if "ISIN" in row and "Percent of Fund" in row), None)
    stated = next((row[1] for row in rows[:header] if len(row) > 1 and row[0] == "Holdings As Of:"), None)
    if header is None or stated is None:
        raise ValueError("tableau ou date introuvable")
    as_of = datetime.strptime(stated, "%d-%b-%Y").date()
    lines: list[Constituent] = []
    for row in rows[header + 1:]:
        if not any(row):
            break
        line = _line(dict(zip(rows[header], row, strict=False)))
        if line:
            lines.append(line)
    if not lines:
        raise ValueError("aucune ligne")
    return Composition(as_of=as_of, lines=lines)


def _line(row: dict[str, str]) -> Constituent | None:
    """None pour une ligne sans poids (« - » des contrats à terme) ou de poids nul."""
    stated = text_or_none(row.get("Percent of Fund"))
    weight = float(stated) if stated else 0.0
    if not weight:
        return None
    isin = text_or_none(row.get("ISIN"))
    sector = text_or_none(row.get("Sector Classification"))
    return Constituent(
        isin=isin, ticker=None, name=row.get("Security Name", "").strip(), weight=weight,
        country=country_code(row.get("Trade Country Name")), sector=sector_label(sector),
        asset_class="Equity" if isin or sector else _NO_CLASS, exchange=None,
    )
