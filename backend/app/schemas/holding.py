from datetime import datetime

from pydantic import BaseModel

from app.schemas.types import Amount, BoundedDatetime, Quantity


class PortfolioHoldingBase(BaseModel):
    account_id: int
    ticker: str
    isin: str | None = None
    asset_name: str
    quantity: Quantity
    buy_price_avg: Quantity | None = None
    currency: str = "EUR"
    etf_profile_id: int | None = None


class PortfolioHoldingCreate(PortfolioHoldingBase):
    cost_basis_eur: Quantity | None = None  # coût de revient EUR total de la ligne (prioritaire sur la conversion au taux du Point Zéro)


class PortfolioHoldingUpdate(BaseModel):
    ticker: str | None = None
    isin: str | None = None
    asset_name: str | None = None
    quantity: Quantity | None = None
    buy_price_avg: Quantity | None = None
    currency: str | None = None
    etf_profile_id: int | None = None
    pays_dividends: bool | None = None
    cost_basis_eur: Quantity | None = None


class PortfolioHoldingRead(PortfolioHoldingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    # Dynamic live market fields
    current_price: float | None = None
    current_price_eur: float | None = None
    quote_currency: str | None = None
    price_date: str | None = None
    price_stale: bool = False
    current_value_eur: float | None = None
    total_invested_eur: float | None = None
    gain_eur: float | None = None
    gain_pct: float | None = None
    is_etf: bool = False
    cost_basis_eur: float | None = None  # coût de revient EUR total de la position

    # Dividendes (EUR) rattachés à ce titre
    pays_dividends: bool | None = None
    dividends_received_eur: float = 0.0
    dividends_12m_eur: float = 0.0
    last_dividend_date: str | None = None
    total_return_eur: float | None = None  # plus-value latente + dividendes reçus
    total_return_pct: float | None = None

    model_config = {"from_attributes": True}


class BaselineHoldingItem(BaseModel):
    ticker: str
    asset_name: str
    isin: str | None = None
    quantity: Quantity
    buy_price_avg: Quantity | None = None
    currency: str = "EUR"
    etf_profile_id: int | None = None
    cost_basis_eur: Quantity | None = None  # absent = on garde la valeur déjà saisie ; null = on l'efface


class BaselineInventoryRequest(BaseModel):
    account_id: int
    date: BoundedDatetime | None = None
    holdings: list[BaselineHoldingItem]


class CostEstimateRead(BaseModel):
    ticker: str
    asset_name: str
    quantity: float
    currency: str
    current_cost: float | None = None
    estimate: float | None = None
    buys: int
    bought_quantity: float
    sold_quantity: float
    coverage: float | None = None
    first_buy: str | None = None
    method: str = "quantities"
    amount_only_buys: int = 0


class ApplyCostLine(BaseModel):
    ticker: str
    buy_price_avg: Amount


class ApplyCostsRequest(BaseModel):
    account_id: int
    items: list[ApplyCostLine]
