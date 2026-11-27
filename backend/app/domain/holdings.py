"""Positions : types d'opérations sur titres, ventes réalisées, résultat du rejeu, estimation du PRU (sans base)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.domain.etf_profiles import match_profile

if TYPE_CHECKING:
    from app.models.etf_profile import EtfProfile

BUY_TYPES = ("versement", "achat")
SELL_TYPES = ("retrait", "vente")
TRADE_TYPES = BUY_TYPES + SELL_TYPES
EPSILON = 1e-9


def normalize_ticker(ticker: str) -> str:
    return ticker.upper().strip()


def is_trade(tx_type: str, ticker: str | None, quantity: float | None) -> bool:
    """Vrai si l'opération fait bouger une position (titre + quantité + type achat/vente)."""
    return bool(ticker) and quantity is not None and quantity > 0 and tx_type in TRADE_TYPES


FUND_QUOTE_TYPES = ("ETF", "MUTUALFUND")
CRYPTO_SUFFIXES = ("-USD", "-EUR")


def is_fund(quote_type: str | None, ticker: str) -> bool:
    """Vrai pour un ETF ou un fonds : type de cotation `ETF`/`MUTUALFUND`, ou ticker de fonds Yahoo (`0P…`)."""
    return quote_type in FUND_QUOTE_TYPES or normalize_ticker(ticker).startswith("0P")


def is_crypto(quote_type: str | None, ticker: str) -> bool:
    """Vrai pour une cryptomonnaie : type `CRYPTOCURRENCY`, ou ticker de paire `BTC-USD` / `BTC-EUR`."""
    return quote_type == "CRYPTOCURRENCY" or normalize_ticker(ticker).endswith(CRYPTO_SUFFIXES)


def isin_missing(isin: str | None, quote_type: str | None, ticker: str) -> bool:
    """Vrai pour une position dont l'ISIN reste à compléter ; une crypto n'a pas d'ISIN."""
    return not (isin or "").strip() and not is_crypto(quote_type, ticker)


def is_etf_holding(quote_type: str | None, ticker: str, isin: str | None, profile: "EtfProfile | None") -> bool:
    """ETF ou fonds : le type du titre fait foi ; type inconnu (cours indisponible), on se rabat sur un profil
    dont le ticker, l'ISIN ou un alias est exactement celui de la position."""
    if is_fund(quote_type, ticker):
        return True
    if quote_type not in (None, "", "UNKNOWN") or profile is None:
        return False
    return match_profile([profile], ticker, isin) is not None


def holding_profile(profiles: "list[EtfProfile]", profile_id: int | None, ticker: str, isin: str | None) -> "EtfProfile | None":
    """Profil rattaché à la position, sinon profil correspondant exactement (parmi `profiles`)."""
    attached = next((p for p in profiles if p.id == profile_id), None) if profile_id else None
    return attached or match_profile(profiles, ticker, isin)


@dataclass
class RealizedSale:
    """Vente rejouée : produit net et coût de revient de la quantité cédée (plus-value réalisée en EUR)."""

    tx_id: int
    date: datetime
    ticker: str
    quantity: float
    proceeds_eur: float | None
    cost_eur: float | None  # coût de revient (EUR, taux des achats) de la quantité vendue
    cost_eur_estimated: bool = False  # coût issu d'une ligne d'inventaire en devise, converti au taux du Point Zéro

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
    cost_eur_estimated: bool = False  # inventaire en devise sans coût EUR saisi : converti au taux du Point Zéro
    discount_eur: float = 0.0  # gain de décote (référence − prix payé) des parts encore détenues, aux taux des achats
    isin: str | None = None
    asset_name: str | None = None
    etf_profile_id: int | None = None
    cutoff: datetime | None = None


@dataclass
class Trade:
    """Achat ou vente rejoué, en EUR : base du portefeuille fantôme (`services/investissement/benchmark.py`)."""

    date: datetime
    ticker: str
    kind: str  # "buy" | "sell"
    quantity: float  # parts achetées, ou vendues (au plus la quantité détenue)
    held_before: float  # parts détenues juste avant l'opération
    amount_eur: float | None  # achat : coût frais compris ; vente : produit net ; None = sans taux de change
    reinvested: bool = False  # achat généré par un dividende réinvesti


@dataclass
class Replay:
    """Résultat du rejeu : positions finales, ventes réalisées et variations de quantité datées."""

    positions: dict[str, Position]
    realized: list[RealizedSale]
    baseline_date: datetime | None
    baseline: dict[str, Position]  # inventaire Point Zéro tel que rejoué
    quantity_events: list[tuple[datetime, str, float]]  # (date, ticker, ±quantité)
    trades: list[Trade] = field(default_factory=list)  # achats et ventes rejoués, dans l'ordre


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


def holding_price_eur(quote_eur: float, buy_price_avg: float | None, currency: str | None,
                      fx_rates: dict[str, float]) -> float:
    """Cours en EUR d'une position ; aucun cours connu : repli sur le PRU, converti de la devise de la position."""
    if quote_eur > 0 or not buy_price_avg:
        return quote_eur
    fx = fx_rates.get((currency or "EUR").upper())
    return buy_price_avg / fx if fx else 0.0


def holding_returns(quantity: float, price_eur: float, cost_basis_eur: float | None, buy_price_avg: float | None,
                    fx: float | None, dividends_total_eur: float) -> dict[str, Any]:
    """Valeur, coût de revient, plus-value et rendement total (dividendes compris) d'une position, en EUR.

    Coût de revient : aux taux historiques des achats si connu, sinon PRU converti au taux du jour (`fx`).
    """
    value_eur = quantity * price_eur if price_eur > 0 else 0.0
    invested_eur = cost_basis_eur
    if invested_eur is None and buy_price_avg and buy_price_avg > 0 and fx:
        invested_eur = quantity * buy_price_avg / fx

    gain_eur = gain_pct = None
    if invested_eur is not None and invested_eur > 0 and value_eur > 0:
        gain_eur = round(value_eur - invested_eur, 2)
        gain_pct = round((gain_eur / invested_eur) * 100.0, 2)

    total_return_eur = total_return_pct = None
    if gain_eur is not None and invested_eur is not None:
        total_return_eur = round(gain_eur + dividends_total_eur, 2)
        total_return_pct = round(total_return_eur / invested_eur * 100.0, 2)
    return {
        "value_eur": value_eur, "invested_eur": invested_eur, "gain_eur": gain_eur, "gain_pct": gain_pct,
        "total_return_eur": total_return_eur, "total_return_pct": total_return_pct,
    }
