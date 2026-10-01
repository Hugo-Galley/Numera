from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EtfHoldingItem(BaseModel):
    name: str
    ticker: Optional[str] = None
    weight: float = Field(ge=0, le=100)


class EtfProfileBase(BaseModel):
    name: str
    ticker: str
    isin: Optional[str] = None
    aliases: List[str] = []
    countries: Dict[str, float] = {}
    sectors: Dict[str, float] = {}
    top_holdings: List[EtfHoldingItem] = []


class EtfProfileCreate(EtfProfileBase):
    pass


class EtfProfileUpdate(BaseModel):
    name: Optional[str] = None
    ticker: Optional[str] = None
    isin: Optional[str] = None
    aliases: Optional[List[str]] = None
    countries: Optional[Dict[str, float]] = None
    sectors: Optional[Dict[str, float]] = None
    top_holdings: Optional[List[EtfHoldingItem]] = None


class EtfProfileRead(EtfProfileBase):
    id: int
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutoDecomposeRequest(BaseModel):
    symbol: str
    name: Optional[str] = None
    isin: Optional[str] = None
