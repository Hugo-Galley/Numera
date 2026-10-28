from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.schemas.transfer_rule import TransferApplyResult, TransferRuleCreate, TransferRuleRead, TransferRuleUpdate
from app.services import transfer_rules as service

router = APIRouter(prefix="/transfer-rules", tags=["transfer-rules"])


@router.get("", response_model=list[TransferRuleRead])
def list_rules(db: Session = Depends(get_db)):
    return service.list_rules(db)


@router.post("", response_model=TransferRuleRead, status_code=201)
def create_rule(payload: TransferRuleCreate, db: Session = Depends(get_db)):
    return service.create_rule(db, payload)


@router.patch("/{rule_id}", response_model=TransferRuleRead)
def update_rule(rule_id: int, payload: TransferRuleUpdate, db: Session = Depends(get_db)):
    return service.update_rule(db, rule_id, payload)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    service.delete_rule(db, rule_id)


@router.post("/apply", response_model=TransferApplyResult)
async def apply_transfer_rules(
    dry_run: bool = Query(default=False),
    rule_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Rattrape tout l'historique avec les règles actives. `dry_run=true` : aperçu sans écriture."""
    return await service.apply_transfer_rules(db, dry_run, rule_id)
