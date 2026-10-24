from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.types import Amount, BoundedDatetime, Quantity


class PortfolioHoldingBase(BaseModel):
    account_id: int
    ticker: str
    isin: Optional[str] = None
    asset_name: str
    quantity: Quantity
    buy_price_avg: Optional[Quantity] = None
    currency: str = "EUR"
    etf_profile_id: Optional[int] = None


class PortfolioHoldingCreate(PortfolioHoldingBase):
    pass


class PortfolioHoldingUpdate(BaseModel):
    ticker: Optional[str] = None
    isin: Optional[str] = None
    asset_name: Optional[str] = None
    quantity: Optional[Quantity] = None
    buy_price_avg: Optional[Quantity] = None
    currency: Optional[str] = None
    etf_profile_id: Optional[int] = None
    pays_dividends: Optional[bool] = None


class PortfolioHoldingRead(PortfolioHoldingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    # Dynamic live market fields
    current_price: Optional[float] = None
    current_price_eur: Optional[float] = None
    quote_currency: Optional[str] = None
    price_date: Optional[str] = None
    price_stale: bool = False
    current_value_eur: Optional[float] = None
    total_invested_eur: Optional[float] = None
    gain_eur: Optional[float] = None
    gain_pct: Optional[float] = None
    is_etf: bool = False

    # Dividendes (EUR) rattachés à ce titre
    pays_dividends: Optional[bool] = None
    dividends_received_eur: float = 0.0
    dividends_12m_eur: float = 0.0
    last_dividend_date: Optional[str] = None
    total_return_eur: Optional[float] = None  # plus-value latente + dividendes reçus
    total_return_pct: Optional[float] = None

    model_config = {"from_attributes": True}


class BaselineHoldingItem(BaseModel):
    ticker: str
    asset_name: str
    isin: Optional[str] = None
    quantity: Quantity
    buy_price_avg: Optional[Quantity] = None
    currency: str = "EUR"
    etf_profile_id: Optional[int] = None


class BaselineInventoryRequest(BaseModel):
    account_id: int
    date: Optional[BoundedDatetime] = None
    holdings: List[BaselineHoldingItem]


class CostEstimateRead(BaseModel):
    ticker: str
    asset_name: str
    quantity: float
    currency: str
    current_cost: Optional[float] = None
    estimate: Optional[float] = None
    buys: int
    bought_quantity: float
    sold_quantity: float
    coverage: Optional[float] = None
    first_buy: Optional[str] = None
    method: str = "quantities"
    amount_only_buys: int = 0


class ApplyCostLine(BaseModel):
    ticker: str
    buy_price_avg: Amount


class ApplyCostsRequest(BaseModel):
    account_id: int
    items: List[ApplyCostLine]
