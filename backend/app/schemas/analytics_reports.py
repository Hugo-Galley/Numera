"""Réponses de `/analytics/{sankey,diversity-scanner,audit/{issue_id}}` et des acquittements `dismiss` / `ignore`."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.etf_profile import EtfCompositionOrigin
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
    source: str  # nom de l'exposition porteuse (deux supports d'un même indice : un seul chemin), ou « En direct »
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
    # Poids de la référence de marché, renormalisé sur sa part connue ; None sans référence ou hors comparaison
    market_pct: float | None


MarketDimensionKey = Literal["companies", "sectors", "countries"]
ExposureKind = Literal["fund", "direct", "crypto"]
PairSource = Literal["prices", "composition", "unknown"]


class DiversityAlert(BaseModel):
    type: str  # « warning » ou « info »
    category: Literal["overweight", "correlated_block", "redundant_pick", "overlap"]
    # Dimension d'une sur-pondération ; None pour les autres catégories
    dimension: MarketDimensionKey | None = None
    title: str
    message: str
    item_name: str
    value_pct: float


class DiversityExposureSupport(BaseModel):
    account_id: int
    account_name: str | None
    ticker: str
    value_eur: float


class DiversityExposureGroup(BaseModel):
    """Positions qui sont la même exposition (même titre, même profil ou même indice), tous comptes confondus."""

    id: str
    name: str
    kind: ExposureKind
    value_eur: float
    weight_pct: float
    supports: list[DiversityExposureSupport]


class DiversityBlock(BaseModel):
    members: list[str]  # noms d'exposition
    weight_pct: float
    mean_rho: float


class DiversityConcentration(BaseModel):
    effective_bets: float  # nombre de paris indépendants (N_eff)
    exposures_count: int
    blocks: list[DiversityBlock]
    pairs_by_source: dict[PairSource, int]


class DiversityGapRow(BaseModel):
    name: str
    portfolio_pct: float
    market_pct: float
    # Nom absent d'un marché connu par son seul top : market_pct est un majorant
    market_pct_is_upper_bound: bool
    gap_pts: float


class DiversityMarketDimension(BaseModel):
    active_share_pct: float
    covered_pct: float  # part du portefeuille décrite et comparée (hors « Non renseigné », liquidités, « Autres »)
    # Faux si un côté n'a rien de comparable (composition inconnue, référence sans pays ou sans secteurs)
    comparable: bool
    rows: list[DiversityGapRow]  # les plus gros écarts, au plus 30


class DiversityMarket(BaseModel):
    """Référence de marché (réglage `market_reference_ticker`, MSCI ACWI par défaut) et écart par dimension."""

    name: str
    ticker: str | None
    companies: DiversityMarketDimension
    sectors: DiversityMarketDimension
    countries: DiversityMarketDimension


class DiversityStockPick(BaseModel):
    key: str
    name: str
    ticker: str
    value_eur: float
    indirect_value_eur: float  # déjà détenu via les fonds
    indirect_pct: float
    correlation_with_core: float | None
    source: PairSource
    redundant: bool


class DiversityCoverage(BaseModel):
    with_prices_pct: float  # part de la valeur avec un historique de cours suffisant
    composition_pct: float  # part de la valeur dont la composition est connue


class DiversityTotals(BaseModel):
    stocks_eur: float
    # Part de `stocks_eur` détenue en direct (actions, cryptos) et via des ETF décomposés
    direct_eur: float
    etf_eur: float
    epargne_eur: float
    courant_eur: float
    fonds_euros_eur: float
    other_eur: float
    wealth_eur: float
    holdings_count: int
    etfs_count: int


class DiversityComposition(EtfCompositionOrigin):
    """ETF synthétique : réplication, indice et référence du fonds détenu ; source, date, lignes et couverture
    des données utilisées (celles de la référence)."""

    profile_id: int
    profile_name: str
    tickers: list[str]
    value_eur: float
    sources: dict[str, str]  # champ → origine (« ishares », « amundi », « spdr », « justetf », « yahoo », « manual »)
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
    exposures: list[DiversityExposureGroup]
    concentration: DiversityConcentration
    market: DiversityMarket | None  # None : référence de marché introuvable (score neutre)
    stock_picking: list[DiversityStockPick]
    coverage: DiversityCoverage


class MarketReferenceSetting(BaseModel):
    ticker: str | None = Field(default=None, max_length=32)  # None / vide : ETF de référence du MSCI ACWI
