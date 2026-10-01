from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PortfolioHoldingBase(BaseModel):
    account_id: int
    ticker: str
    isin: Optional[str] = None
    asset_name: str
    quantity: float = Field(ge=0)
    buy_price_avg: Optional[float] = Field(default=None, ge=0)
    currency: str = "EUR"
    etf_profile_id: Optional[int] = None


class PortfolioHoldingCreate(PortfolioHoldingBase):
    pass


class PortfolioHoldingUpdate(BaseModel):
    ticker: Optional[str] = None
    isin: Optional[str] = None
    asset_name: Optional[str] = None
    quantity: Optional[float] = Field(default=None, ge=0)
    buy_price_avg: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None
    etf_profile_id: Optional[int] = None


class PortfolioHoldingRead(PortfolioHoldingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    # Dynamic live market fields
    current_price: Optional[float] = None
    current_price_eur: Optional[float] = None
    current_value_eur: Optional[float] = None
    total_invested_eur: Optional[float] = None
    gain_eur: Optional[float] = None
    gain_pct: Optional[float] = None
    is_etf: bool = False

    model_config = {"from_attributes": True}


class BaselineHoldingItem(BaseModel):
    ticker: str
    asset_name: str
    isin: Optional[str] = None
    quantity: float = Field(ge=0)
    buy_price_avg: Optional[float] = None
    currency: str = "EUR"
    etf_profile_id: Optional[int] = None


class BaselineInventoryRequest(BaseModel):
    account_id: int
    holdings: List[BaselineHoldingItem]
