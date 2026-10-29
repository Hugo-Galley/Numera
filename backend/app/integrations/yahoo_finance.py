"""Yahoo Finance : recherche de titres et cours (endpoint chart), via `httpx`.

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
