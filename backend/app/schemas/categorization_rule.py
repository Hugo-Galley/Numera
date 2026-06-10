from pydantic import BaseModel
from typing import Optional

class CategorizationRuleBase(BaseModel):
    pattern: str
    category_id: Optional[int] = None
    transaction_type: Optional[str] = None
    merchant_name: Optional[str] = None
    priority: int = 0

class CategorizationRuleCreate(CategorizationRuleBase):
    pass

class CategorizationRuleUpdate(BaseModel):
    pattern: Optional[str] = None
    category_id: Optional[int] = None
    transaction_type: Optional[str] = None
    merchant_name: Optional[str] = None
    priority: Optional[int] = None

class CategorizationRuleRead(CategorizationRuleBase):
    id: int

    model_config = {"from_attributes": True}
