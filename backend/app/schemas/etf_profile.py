from datetime import date, datetime

from pydantic import BaseModel, Field


class EtfHoldingItem(BaseModel):
    name: str
    ticker: str | None = None
    weight: float = Field(ge=0, le=100)


class EtfProfileBase(BaseModel):
    name: str
    ticker: str
    isin: str | None = None
    aliases: list[str] = []
    countries: dict[str, float] = {}
    sectors: dict[str, float] = {}
    top_holdings: list[EtfHoldingItem] = []


class EtfProfileCreate(EtfProfileBase):
    pass


class EtfProfileUpdate(BaseModel):
    name: str | None = None
    ticker: str | None = None
    isin: str | None = None
    aliases: list[str] | None = None
    countries: dict[str, float] | None = None
    sectors: dict[str, float] | None = None
    top_holdings: list[EtfHoldingItem] | None = None


class EtfCompositionOrigin(BaseModel):
    """D'où vient une composition, de quand elle date et quelle part du fonds elle décrit."""

    # Source des données : ishares | amundi | spdr | justetf | yahoo (None = jamais obtenue ou saisie seule)
    provider: str | None = None
    replication: str = "unknown"  # physical | synthetic | unknown
    index_name: str | None = None
    # ETF synthétique : profil de l'ETF physique de référence qui donne son exposition (None = indice non reconnu)
    exposure_profile_id: int | None = None
    exposure_profile_name: str | None = None
    composition_as_of: date | None = None
    coverage_pct: float | None = None  # % du fonds décrit
    lines_count: int = 0  # 0 = agrégats ou premières lignes seulement


class EtfProfileRead(EtfProfileBase, EtfCompositionOrigin):
    id: int
    is_system: bool
    # Source de chaque champ de composition : ishares | amundi | spdr | justetf | yahoo | manual (absent = non renseigné)
    composition_sources: dict[str, str] = {}
    composition_refreshed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutoDecomposeRequest(BaseModel):
    symbol: str
    name: str | None = None
    isin: str | None = None


class EtfRefreshResult(BaseModel):
    refreshed: int
