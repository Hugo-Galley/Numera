"""Réponses de `/market/*` et de `/holdings/suggestions`."""
from datetime import datetime

from pydantic import BaseModel


class MarketAsset(BaseModel):
    """Résultat de recherche : profil ETF local ou valeur Yahoo Finance."""

    symbol: str
    name: str
    isin: str | None
    type: str
    exchange: str
    currency: str
    etf_profile_id: int | None
    is_custom_etf: bool


class SymbolValidation(BaseModel):
    valid: bool
    symbol: str
    name: str | None
    isin: str | None
    type: str | None
    currency: str
    price: float | None
    price_eur: float | None
    etf_profile_id: int | None


class MarketQuote(BaseModel):
    """Cotation du jour. `price == 0` signifie « aucun cours connu » ; `stale` : dernier cours enregistré."""

    symbol: str
    name: str
    price: float
    currency: str
    price_eur: float
    type: str
    price_date: str | None
    stale: bool
    expires_at: datetime | None = None


class HoldingSuggestion(BaseModel):
    name: str
    ticker: str
    isin: str | None
    historical_net_invested: float
    tx_count: int
    etf_profile_id: int | None
    is_etf: bool
