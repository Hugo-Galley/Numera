from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.schemas.categorization_rule import CategorizationRuleCreate, CategorizationRuleRead, CategorizationRuleUpdate
from app.services.budget import categorization_rules as service

router = APIRouter(prefix="/categorization-rules", tags=["categorization-rules"])


@router.get("/", response_model=List[CategorizationRuleRead])
def list_rules(db: Session = Depends(get_db)):
    return service.list_rules(db)


@router.post("/", response_model=CategorizationRuleRead, status_code=201)
def create_rule(payload: CategorizationRuleCreate, db: Session = Depends(get_db)):
    return service.create_rule(db, payload)


@router.patch("/{rule_id}", response_model=CategorizationRuleRead)
def update_rule(rule_id: int, payload: CategorizationRuleUpdate, db: Session = Depends(get_db)):
    return service.update_rule(db, rule_id, payload)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    service.delete_rule(db, rule_id)


@router.post("/apply-all", status_code=200)
def apply_rules_to_transactions(db: Session = Depends(get_db)):
    """Applique les règles aux transactions existantes (catégorie jamais écrasée, soldes recalculés)."""
    return service.apply_rules_to_transactions(db)
