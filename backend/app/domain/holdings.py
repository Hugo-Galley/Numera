"""Positions : types d'opérations sur titres, ventes réalisées, résultat du rejeu, estimation du PRU (sans base)."""
from dataclasses import dataclass
from datetime import datetime

BUY_TYPES = ("versement", "achat")
SELL_TYPES = ("retrait", "vente")
TRADE_TYPES = BUY_TYPES + SELL_TYPES
EPSILON = 1e-9


def normalize_ticker(ticker: str) -> str:
    return ticker.upper().strip()


def is_trade(tx_type: str, ticker: str | None, quantity: float | None) -> bool:
    """Vrai si l'opération fait bouger une position (titre + quantité + type achat/vente)."""
    return bool(ticker) and bool(quantity) and quantity > 0 and tx_type in TRADE_TYPES


@dataclass
class RealizedSale:
    """Vente rejouée : produit net et coût de revient de la quantité cédée (plus-value réalisée en EUR)."""

    tx_id: int
    date: datetime
    ticker: str
    quantity: float
    proceeds_eur: float | None
    cost_eur: float | None  # coût de revient (EUR, taux des achats) de la quantité vendue

    @property
    def realized_eur(self) -> float | None:
        if self.proceeds_eur is None or self.cost_eur is None:
            return None
        return self.proceeds_eur - self.cost_eur


@dataclass
class Position:
    ticker: str
    currency: str
    quantity: float = 0.0
    cost: float | None = 0.0  # devise de la position ; None = PRU inconnu
    cost_eur: float | None = 0.0
    isin: str | None = None
    asset_name: str | None = None
    etf_profile_id: int | None = None
    cutoff: datetime | None = None


@dataclass
class Replay:
    """Résultat du rejeu : positions finales, ventes réalisées et variations de quantité datées."""

    positions: dict[str, Position]
    realized: list[RealizedSale]
    baseline_date: datetime | None
    baseline: dict[str, Position]  # inventaire Point Zéro tel que rejoué
    quantity_events: list[tuple[datetime, str, float]]  # (date, ticker, ±quantité)


@dataclass
class CostEstimate:
    ticker: str
    asset_name: str
    quantity: float  # quantité de l'inventaire
    currency: str
    current_cost: float | None  # PRU actuellement saisi
    estimate: float | None  # PRU estimé depuis les achats antérieurs à l'inventaire
    buys: int
    bought_quantity: float
    sold_quantity: float
    first_buy: datetime | None
    method: str = "quantities"  # "quantities" : prix × quantités saisis ; "amounts" : montants versés ÷ parts détenues
    amount_only_buys: int = 0

    @property
    def coverage(self) -> float | None:
        """Part de l'inventaire expliquée par les opérations antérieures (1.0 = tout)."""
        if self.quantity <= EPSILON or self.method == "amounts":
            return None
        return (self.bought_quantity - self.sold_quantity) / self.quantity
