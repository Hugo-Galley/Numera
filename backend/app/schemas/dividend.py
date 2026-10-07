from typing import List, Optional

from pydantic import BaseModel


class DividendTotals(BaseModel):
    count: int = 0
    net_eur: float = 0.0
    withholding_eur: float = 0.0
    gross_eur: float = 0.0
    last_12m_eur: float = 0.0


class DividendMonth(BaseModel):
    month: str  # YYYY-MM
    net_eur: float


class DividendYear(BaseModel):
    year: int
    count: int
    net_eur: float
    withholding_eur: float
    gross_eur: float


class DividendTicker(BaseModel):
    ticker: str
    asset_name: str
    count: int
    total_eur: float
    last_12m_eur: float
    last_date: Optional[str] = None
    # 12 derniers mois ÷ coût de revient / valeur actuelle de la position (None sans position ou sans coût)
    yield_on_cost_pct: Optional[float] = None
    current_yield_pct: Optional[float] = None


class DividendUnlinked(BaseModel):
    count: int = 0
    total_eur: float = 0.0


class DividendSummary(BaseModel):
    totals: DividendTotals
    by_month: List[DividendMonth]
    by_year: List[DividendYear]
    by_ticker: List[DividendTicker]
    unlinked: DividendUnlinked
