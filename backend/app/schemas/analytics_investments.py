"""Réponses de `/analytics/investments*`, `/analytics/patrimoine-allocation` et `/analytics/asset-allocation/suggestions`.

Les routes à champs facultatifs (`/investments`, `/investments/{id}`, `…/performance-history`) se servent avec
`response_model_exclude_unset=True` : une clé que le service ne produit pas n'apparaît pas dans la réponse.
"""
from pydantic import BaseModel


class InvestmentOverviewItem(BaseModel):
    """Un compte dans la vue d'ensemble (EUR). `gain_eur` et `performance_pct` sont nuls si la valeur est périmée."""

    account_id: int
    account_name: str
    total_verse: float
    total_retire: float
    net_invested: float
    current_value: float
    gain_eur: float | None
    performance_pct: float | None
    currency: str
    value_source: str  # « positions », « snapshot » ou « none »
    value_stale: bool
    xirr_pct: float | None = None
    unrealized_eur: float | None = None
    realized_eur: float | None = None
    dividends_eur: float | None = None


class InvestmentsOverview(BaseModel):
    total_net_invested: float
    total_current_value: float
    total_gain_eur: float
    total_performance_pct: float
    items: list[InvestmentOverviewItem]


class InvestmentBaseline(BaseModel):
    date: str | None
    value: float


class InvestmentTotals(BaseModel):
    total_verse: float
    total_retire: float
    net_invested: float
    current_value: float
    gain_eur: float
    performance_pct: float
    value_source: str
    snapshot_value: float | None


class InvestmentMovement(BaseModel):
    """Opération de placement ou transaction bancaire du compte (devise du compte)."""

    id: int
    date: str
    type: str
    amount: float
    original_amount: float
    currency: str
    note: str | None
    asset_class: str | None = None
    sector: str | None = None
    geographic_zone: str | None = None
    is_regular: bool | None = None


class InvestmentValuePoint(BaseModel):
    id: int
    date: str
    current_value: float
    current_value_raw: float
    is_zero_point: bool
    note: str | None


class InvestmentAccountDetail(BaseModel):
    account_id: int
    account_name: str
    currency: str
    baseline: InvestmentBaseline
    totals: InvestmentTotals
    transactions: list[InvestmentMovement]
    value_series: list[InvestmentValuePoint]


class PerformancePoint(BaseModel):
    date: str
    net_invested: float
    current_value: float
    gain_eur: float
    performance_pct: float
    is_zero_point: bool


class PerformanceHistory(BaseModel):
    items: list[PerformancePoint]
    value_source: str | None = None


class AllocationAccount(BaseModel):
    account_id: int
    account_name: str
    current_value: float
    net_invested: float
    gain_eur: float
    performance_pct: float | None  # None sans capital net investi positif
    percentage: float
    currency: str
    value_source: str


class InvestmentsAllocation(BaseModel):
    total_current_value: float
    total_net_invested: float
    total_gain_eur: float
    total_performance_pct: float
    items: list[AllocationAccount]


class AllocationAccountShare(BaseModel):
    account_id: int
    account_name: str
    value: float
    percentage_of_group: float


class AllocationGroup(BaseModel):
    name: str
    value: float
    percentage: float
    items: list[AllocationAccountShare]


class InvestmentsAllocationAdvanced(BaseModel):
    total_value_eur: float
    by_asset_class: list[AllocationGroup]
    by_sector: list[AllocationGroup]
    by_geographic_zone: list[AllocationGroup]


class PatrimoineItem(BaseModel):
    account_id: int
    account_name: str
    institution: str | None
    type: str
    currency: str
    balance: float
    balance_eur: float
    percentage: float
    logo: str | None


class PatrimoineAllocation(BaseModel):
    total_patrimoine: float
    total_debts_eur: float
    net_patrimoine_eur: float
    items: list[PatrimoineItem]


class AllocationSuggestions(BaseModel):
    asset_classes: list[str]
    sectors: list[str]
    geographic_zones: list[str]
