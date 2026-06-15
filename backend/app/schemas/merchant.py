from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class MerchantAliasBase(BaseModel):
    label: str

class MerchantAliasCreate(MerchantAliasBase):
    pass

class MerchantAlias(MerchantAliasBase):
    id: int
    merchant_id: int
    
    model_config = ConfigDict(from_attributes=True)

class MerchantBase(BaseModel):
    name: str
    category_id: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class MerchantCreate(MerchantBase):
    aliases: Optional[List[str]] = []

class MerchantUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class MerchantRead(MerchantBase):
    id: int
    aliases: List[MerchantAlias] = []

    model_config = ConfigDict(from_attributes=True)
