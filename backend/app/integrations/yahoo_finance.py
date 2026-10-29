"""Yahoo Finance : recherche de titres, cours (endpoint chart) et composition des ETF (quoteSummary), via `httpx`.

Aucune écriture en base ni règle métier : le service `services/market` décide quoi stocker et quel repli appliquer.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}
SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"


def client(timeout: float) -> httpx.AsyncClient:
    """Client HTTP aux en-têtes attendus par Yahoo (à utiliser en `async with`)."""
    return httpx.AsyncClient(headers=HEADERS, timeout=timeout)


async def fetch_chart(http_client: httpx.AsyncClient, sym: str, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Appelle l'endpoint chart de Yahoo (query2 puis query1) et renvoie le premier résultat."""
    quoted_sym = quote(sym, safe="")
    for host in ("query2", "query1"):
        resp = await http_client.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{quoted_sym}", params=params)
        if resp.status_code == 200:
            res_list = resp.json().get("chart", {}).get("result") or []
            return res_list[0] if res_list else None
    return None


async def search_quotes(query: str) -> List[Dict[str, Any]]:
    """Résultats bruts (`quotes`) de la recherche publique Yahoo ; liste vide si Yahoo répond en erreur."""
    async with client(6.0) as http_client:
        resp = await http_client.get(SEARCH_URL, params={"q": query, "quotesCount": 10, "newsCount": 0})
        if resp.status_code != 200:
            return []
        return resp.json().get("quotes", [])


# ── Composition des ETF et fonds (module `topHoldings` de quoteSummary) ──────────
# Yahoo fournit la répartition sectorielle et, pour les ETF à réplication physique, les 10 premières lignes ;
# jamais la répartition par pays.

YAHOO_SECTOR_LABELS: Dict[str, str] = {
    "technology": "Technologie",
    "financial_services": "Finance",
    "healthcare": "Santé",
    "consumer_cyclical": "Consommation discrétionnaire",
    "consumer_defensive": "Biens de consommation",
    "industrials": "Industrie",
    "communication_services": "Services de communication",
    "basic_materials": "Matériaux",
    "energy": "Énergie",
    "utilities": "Services aux collectivités",
    "realestate": "Immobilier",
}

QUOTE_SUMMARY_URL = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"

# quoteSummary exige un cookie de consentement et un « crumb » associé ; on les garde en mémoire
_yahoo_auth: Dict[str, Any] = {"cookies": None, "crumb": None}


class YahooUnavailable(Exception):
    """Yahoo injoignable ou réponse inexploitable (différent de « pas de données pour ce titre »)."""


async def ensure_crumb(http_client: httpx.AsyncClient, force: bool = False) -> str:
    if _yahoo_auth["crumb"] and not force:
        http_client.cookies.update(_yahoo_auth["cookies"])
        return _yahoo_auth["crumb"]
    # fc.yahoo.com répond 404 mais dépose le cookie A3 nécessaire au crumb
    # (le crumb est servi en text/plain : Accept: application/json donnerait un 406)
    await http_client.get("https://fc.yahoo.com", headers={"Accept": "*/*"}, follow_redirects=True)
    resp = await http_client.get("https://query2.finance.yahoo.com/v1/test/getcrumb", headers={"Accept": "*/*"})
    crumb = resp.text.strip()
    if resp.status_code != 200 or not crumb or "<" in crumb:
        raise YahooUnavailable(f"crumb Yahoo indisponible (HTTP {resp.status_code})")
    _yahoo_auth["crumb"] = crumb
    _yahoo_auth["cookies"] = dict(http_client.cookies)
    return crumb


def parse_top_holdings(top: Dict[str, Any]) -> Dict[str, Any]:
    sectors: Dict[str, float] = {}
    for entry in top.get("sectorWeightings") or []:
        for key, value in entry.items():
            weight = round(float((value or {}).get("raw") or 0.0) * 100, 2)
            if weight > 0:
                label = YAHOO_SECTOR_LABELS.get(key, key.replace("_", " ").capitalize())
                sectors[label] = round(sectors.get(label, 0.0) + weight, 2)

    holdings: List[Dict[str, Any]] = []
    for h in top.get("holdings") or []:
        weight = round(float((h.get("holdingPercent") or {}).get("raw") or 0.0) * 100, 2)
        name = h.get("holdingName") or h.get("symbol")
        if name and weight > 0:
            holdings.append({"name": name, "ticker": h.get("symbol") or None, "weight": weight})

    return {"sectors": sectors, "top_holdings": holdings}


async def fetch_composition(symbol: str) -> Optional[Dict[str, Any]]:
    """Composition publiée par Yahoo pour `symbol`.

    Renvoie None si Yahoo ne connaît pas le titre, un dict (éventuellement vide) sinon.
    Lève YahooUnavailable si Yahoo est injoignable.
    """
    cleaned = symbol.strip().upper()
    try:
        async with client(8.0) as http_client:
            crumb = await ensure_crumb(http_client)
            params = {"modules": "topHoldings,quoteType", "crumb": crumb}
            url = QUOTE_SUMMARY_URL.format(symbol=cleaned)
            resp = await http_client.get(url, params=params)
            if resp.status_code in (401, 403):
                params["crumb"] = await ensure_crumb(http_client, force=True)
                resp = await http_client.get(url, params=params)
    except httpx.HTTPError as e:
        raise YahooUnavailable(str(e)) from e

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise YahooUnavailable(f"quoteSummary {cleaned} : HTTP {resp.status_code}")

    try:
        result = (resp.json().get("quoteSummary") or {}).get("result") or []
    except ValueError as e:
        raise YahooUnavailable(f"quoteSummary {cleaned} : réponse illisible") from e
    if not result:
        return None

    data = result[0]
    quote_type = data.get("quoteType") or {}
    composition = parse_top_holdings(data.get("topHoldings") or {})
    composition["name"] = quote_type.get("longName") or quote_type.get("shortName")
    composition["quote_type"] = quote_type.get("quoteType")
    return composition
