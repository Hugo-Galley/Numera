from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_label(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("ne peut pas être vide")
    return value


class MerchantAliasBase(BaseModel):
    label: str = Field(max_length=200)

    _label = field_validator("label")(_clean_label)

class MerchantAliasCreate(MerchantAliasBase):
    pass

class MerchantAlias(MerchantAliasBase):
    id: int
    merchant_id: int

    model_config = ConfigDict(from_attributes=True)

class MerchantBase(BaseModel):
    name: str = Field(max_length=120)
    category_id: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class MerchantCreate(MerchantBase):
    aliases: Optional[List[str]] = []

    _name = field_validator("name")(_clean_label)

    @field_validator("aliases")
    @classmethod
    def _aliases(cls, value):
        cleaned = [_clean_label(a) for a in (value or [])]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("alias en double dans la liste")
        return cleaned

class MerchantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)

    @field_validator("name")
    @classmethod
    def _name(cls, value):
        return None if value is None else _clean_label(value)

    category_id: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class MerchantRead(MerchantBase):
    id: int
    aliases: List[MerchantAlias] = []

    model_config = ConfigDict(from_attributes=True)
