from datetime import date

from pydantic import BaseModel


class PortfolioLine(BaseModel):
    ticker: str
    asset_name: str
    quantity: float
    currency: str
    avg_cost: float | None = None
    cost_eur: float | None = None
    price: float | None = None
    price_currency: str | None = None
    price_date: str | None = None
    price_stale: bool = True
    priced: bool = False
    value_eur: float
    unrealized_eur: float | None = None
    unrealized_pct: float | None = None
    unrealized_local: float | None = None  # plus-value en devise du titre
    fx_effect_eur: float | None = None  # part de la plus-value latente due au change
    discount_eur: float | None = None  # part due à la décote d'achat (cours de référence saisi)
    market_gain_eur: float | None = None  # part due au cours depuis l'achat (plus-value latente − décote)


class RealizedYear(BaseModel):
    year: int
    realized_eur: float
    proceeds_eur: float
    sales: int


class ReconciliationPoint(BaseModel):
    date: str
    snapshot_value: float
    computed_value: float
    gap: float
    gap_pct: float | None = None
    flagged: bool = False


class HistoryPoint(BaseModel):
    date: str
    value: float
    net_invested: float
    gain: float
    performance_pct: float | None = None


class Drawdown(BaseModel):
    """Pire baisse d'un sommet à un creux sur l'indice de performance neutre des flux (TWR chaîné)."""

    max_drawdown_pct: float  # ≤ 0
    peak_date: date | None = None
    trough_date: date | None = None
    recovery_date: date | None = None  # None : pas encore revenu au sommet
    current_drawdown_pct: float  # baisse actuelle sous le plus haut (≤ 0)


class SnapshotRef(BaseModel):
    date: str
    value: float


class PortfolioRead(BaseModel):
    account_id: int
    account_name: str
    held_for: str | None = None  # nom du tiers si le compte est détenu pour quelqu'un d'autre
    currency: str
    valued_by_positions: bool
    value_source: str  # "positions" | "snapshot"
    baseline_date: str | None = None
    # Montants en devise du compte (le suffixe _eur indique la conversion au taux du jour)
    value: float
    value_eur: float
    positions_value_eur: float
    cash: float
    net_invested: float
    net_invested_eur: float
    gain: float
    gain_eur: float
    performance_pct: float | None = None
    xirr_pct: float | None = None
    twr_pct: float | None = None
    period_days: int = 0
    # Montants en EUR (coûts de revient aux taux des achats)
    unrealized_eur: float | None = None
    unrealized_pct: float | None = None
    fx_effect_eur: float | None = None
    discount_eur: float | None = None  # part de la plus-value latente due à la décote d'achat
    market_gain_eur: float | None = None  # part due au cours depuis l'achat
    lines_without_cost: list[str] = []
    realized_eur: float = 0.0
    realized_unknown_sales: int = 0
    realized_by_year: list[RealizedYear] = []
    dividends_eur: float = 0.0
    dividends_12m_eur: float = 0.0
    withholding_eur: float = 0.0
    fees_eur: float = 0.0
    lines: list[PortfolioLine] = []
    stale_tickers: list[str] = []
    snapshot: SnapshotRef | None = None
    reconciliation: list[ReconciliationPoint] | None = None
    history: list[HistoryPoint] | None = None
    drawdown: Drawdown | None = None
    warnings: list[str] = []


class PortfolioOverview(BaseModel):
    """Vue globale : somme (EUR) des comptes titres à soi valorisés par leurs positions."""

    accounts: list[PortfolioRead]
    # Comptes détenus pour un tiers : affichés à part, jamais comptés dans les sommes ci-dessous
    third_party_accounts: list[PortfolioRead] = []
    value_eur: float
    net_invested_eur: float
    gain_eur: float
    performance_pct: float | None = None
    xirr_pct: float | None = None
    drawdown: Drawdown | None = None
    unrealized_eur: float | None = None
    realized_eur: float
    realized_by_year: list[RealizedYear]
    dividends_eur: float
    dividends_12m_eur: float
    fees_eur: float
