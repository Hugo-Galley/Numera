from datetime import datetime

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


class EtfProfileRead(EtfProfileBase):
    id: int
    is_system: bool
    # Source de chaque champ de composition : yahoo | preset | manual (absent = non renseigné)
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
