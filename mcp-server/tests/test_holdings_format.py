"""Tableau `list_holdings` : le prix moyen d'achat est dans la devise de la position, pas en EUR."""
import os

os.environ.setdefault("MCP_TRANSPORT", "streamable-http")
os.environ.setdefault("MCP_API_URL", "http://backend:8001")

import httpx

from numera_mcp.tools import investissement


def test_list_holdings_shows_buy_price_currency(monkeypatch):
    # Arrange : une position en USD dont le PRU est stocké en dollars
    holding = {
        "id": 16, "account_id": 4, "ticker": "ASML", "asset_name": "ASML", "quantity": 0.18599239,
        "buy_price_avg": 1656.5194, "currency": "USD", "current_price_eur": 1264.9968,
        "current_value_eur": 235.28, "total_invested_eur": 274.88, "gain_eur": -39.6, "gain_pct": -14.41,
    }
    monkeypatch.setattr(investissement.api, "get", lambda *a, **kw: httpx.Response(200, json=[holding]))

    # Act
    table = investissement.list_holdings(4)

    # Assert : la colonne porte la devise, sans laisser croire à un prix en EUR
    header = table.splitlines()[2]
    assert "px_achat_moy" in header and "devise" in header
    assert "USD" in table.splitlines()[4]
