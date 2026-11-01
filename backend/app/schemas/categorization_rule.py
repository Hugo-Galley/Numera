
from pydantic import BaseModel, Field, field_validator

from app.domain.finance import normalize_transaction_type


def _check_pattern(value: str | None) -> str | None:
    if value is None:
        return value
    value = value.strip()
    if not value:
        raise ValueError("pattern ne peut pas être vide (il correspondrait à toutes les transactions)")
    return value


def _check_type(value: str | None) -> str | None:
    """Type cible normalisé ; `Solde Initial` n'est jamais une cible de règle."""
    if value is None:
        return value
    try:
        normalized = normalize_transaction_type(value)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    if normalized == "Solde Initial":
        raise ValueError("Solde Initial ne peut pas être cible d'une règle")
    return normalized


class CategorizationRuleBase(BaseModel):
    pattern: str = Field(max_length=200)
    category_id: int | None = None
    transaction_type: str | None = None  # None = ne change pas le type
    merchant_name: str | None = None
    priority: int = 0

    _pattern = field_validator("pattern")(_check_pattern)
    _type = field_validator("transaction_type")(_check_type)

class CategorizationRuleCreate(CategorizationRuleBase):
    pass

class CategorizationRuleUpdate(BaseModel):
    pattern: str | None = Field(default=None, max_length=200)
    category_id: int | None = None
    transaction_type: str | None = None
    merchant_name: str | None = None
    priority: int | None = None

    _pattern = field_validator("pattern")(_check_pattern)
    _type = field_validator("transaction_type")(_check_type)

class CategorizationRuleRead(CategorizationRuleBase):
    id: int

    model_config = {"from_attributes": True}
