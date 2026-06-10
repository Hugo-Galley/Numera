from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction
from app.schemas.categorization_rule import CategorizationRuleCreate, CategorizationRuleRead, CategorizationRuleUpdate
from app.core.finance import normalize_transaction_type

router = APIRouter(prefix="/categorization-rules", tags=["categorization-rules"])

@router.get("/", response_model=List[CategorizationRuleRead])
def list_rules(db: Session = Depends(get_db)):
    return db.query(CategorizationRule).order_by(CategorizationRule.priority.desc(), CategorizationRule.id.desc()).all()

@router.post("/", response_model=CategorizationRuleRead, status_code=201)
def create_rule(payload: CategorizationRuleCreate, db: Session = Depends(get_db)):
    rule = CategorizationRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.patch("/{rule_id}", response_model=CategorizationRuleRead)
def update_rule(rule_id: int, payload: CategorizationRuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(rule, key, value)
    
    db.commit()
    db.refresh(rule)
    return rule

@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()

@router.post("/apply-all", status_code=200)
def apply_rules_to_transactions(db: Session = Depends(get_db)):
    """Apply all rules to existing transactions that don't have a category or match patterns."""
    rules = db.query(CategorizationRule).order_by(CategorizationRule.priority.desc()).all()
    transactions = db.query(Transaction).all()
    
    modified_count = 0
    for tx in transactions:
        matched = False
        for rule in rules:
            pattern = rule.pattern.lower()
            if pattern in (tx.merchant or "").lower() or pattern in (tx.note or "").lower():
                if rule.category_id:
                    tx.category_id = rule.category_id
                if rule.transaction_type:
                    tx.type = rule.transaction_type
                if rule.merchant_name:
                    tx.merchant = rule.merchant_name
                matched = True
                modified_count += 1
                break # Only apply first matching rule by priority
                
    db.commit()
    return {"modified_count": modified_count}
