from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.etf_profile import EtfProfileRead


class WeightRow(BaseModel):
    name: str  # donnée : pays alpha-3, secteur, « Non renseigné », « Liquidités et dérivés »
    weight: float  # % du fonds


class EtfSheetLine(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    ticker: str | None = None
    isin: str | None = None
    weight: float  # % du fonds ; négatif possible (dérivés)
    country: str | None = None
    sector: str
    asset_class: str


class EtfSheet(BaseModel):
    profile: EtfProfileRead
    # Les champs suivants décrivent le profil d'exposition : la référence d'indice d'un synthétique, sinon le fonds
    exposure_profile_id: int | None = None
    exposure_profile_name: str | None = None
    provider: str | None = None
    composition_as_of: date | None = None
    coverage_pct: float
    lines_count: int
    has_full_list: bool
    held_value_eur: float  # positions à soi rattachées à ce fonds
    countries: list[WeightRow]
    sectors: list[WeightRow]
    lines: list[EtfSheetLine]  # poids décroissants
    top_holdings: list[dict[str, Any]]  # seulement sans liste complète
