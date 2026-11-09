"""Réponses de `/analytics/{sankey,diversity-scanner,audit/{issue_id}}` et des acquittements `dismiss` / `ignore`."""
from datetime import datetime

from pydantic import BaseModel

from app.schemas.transaction import TransactionRead


class SankeyNode(BaseModel):
    name: str
    color: str | None = None
    category_id: int | None = None


class SankeyLink(BaseModel):
    source: int
    target: int
    value: float
    color: str | None = None


class Sankey(BaseModel):
    """Servi avec `response_model_exclude_unset=True` : `color` et `category_id` n'existent pas sur tous les nœuds."""

    nodes: list[SankeyNode]
    links: list[SankeyLink]


class DuplicateGroup(BaseModel):
    key: str
    count: int
    transactions: list[TransactionRead]


class TransferPair(BaseModel):
    sortie: TransactionRead
    entree: TransactionRead


class AuditIssueDetails(BaseModel):
    """Détail d'un point d'audit. Une seule des trois listes est présente selon `issue_id`
    (servi avec `response_model_exclude_unset=True`)."""

    issue_id: str
    transactions: list[TransactionRead] | None = None
    duplicate_groups: list[DuplicateGroup] | None = None
    transfer_pairs: list[TransferPair] | None = None


class StatusResponse(BaseModel):
    status: str  # « success » ou « ok »


class DiversityHolding(BaseModel):
    id: int
    account_id: int
    ticker: str
    isin: str | None
    name: str | None
    quantity: float
    price_eur: float
    value_eur: float
    etf_profile_id: int | None
    is_etf: bool


class DiversitySource(BaseModel):
    source: str  # ticker de l'ETF porteur, ou « En direct »
    pct_in_source: float
    value_eur: float


class DiversityCompany(BaseModel):
    name: str
    ticker: str | None
    direct_value_eur: float
    indirect_value_eur: float
    total_value_eur: float
    pct_stocks: float
    pct_total_wealth: float
    sources: list[DiversitySource]
    has_overlap: bool


class DiversityExposure(BaseModel):
    name: str
    value_eur: float
    percentage_stocks: float
    percentage_total_wealth: float


class DiversityAlert(BaseModel):
    type: str  # « danger », « warning » ou « info »
    category: str  # « company », « overlap », « country » ou « sector »
    title: str
    message: str
    item_name: str
    value_pct: float


class DiversityTotals(BaseModel):
    stocks_eur: float
    epargne_eur: float
    courant_eur: float
    fonds_euros_eur: float
    other_eur: float
    wealth_eur: float
    holdings_count: int
    etfs_count: int


class DiversityComposition(BaseModel):
    profile_id: int
    profile_name: str
    tickers: list[str]
    value_eur: float
    sources: dict[str, str]  # champ → origine (« yahoo », « preset », « manual »)
    refreshed_at: datetime | None


class DiversityScanner(BaseModel):
    score: float
    score_label: str
    totals: DiversityTotals
    top_underlying_companies: list[DiversityCompany]
    countries: list[DiversityExposure]
    sectors: list[DiversityExposure]
    alerts: list[DiversityAlert]
    holdings: list[DiversityHolding]
    etf_compositions: list[DiversityComposition]
