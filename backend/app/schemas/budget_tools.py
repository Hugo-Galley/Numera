"""Réponses des outils de classement et de rapprochement : règles de catégories, marchands, virements, dividendes."""
from pydantic import BaseModel, ConfigDict

from app.schemas.investment import InvestmentTransactionRead
from app.schemas.transaction import TransactionRead


class ModifiedCount(BaseModel):
    modified_count: int


class NormalizedCount(BaseModel):
    normalized_count: int


class UnnormalizedLabel(BaseModel):
    label: str
    count: int


class PotentialTransfer(BaseModel):
    """Virement interne suggéré : jambes complètes (la sortie est toujours une transaction)."""

    model_config = ConfigDict(from_attributes=True)

    sortie: TransactionRead
    entree: TransactionRead | InvestmentTransactionRead
    type: str  # regular | investment
    confidence: str  # high | medium
    ambiguous: bool
    day_gap: int


class DividendLinkEntry(BaseModel):
    id: int
    date: str
    note: str | None
    amount: float
    currency: str


class DividendLinkMatch(DividendLinkEntry):
    ticker: str


class DividendLinkResult(BaseModel):
    applied: bool
    matched: list[DividendLinkMatch]
    unmatched: list[DividendLinkEntry]
