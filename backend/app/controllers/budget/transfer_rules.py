from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.core.sync_bridge import run_async
from app.schemas.transfer_rule import TransferApplyResult, TransferRuleCreate, TransferRuleRead, TransferRuleUpdate
from app.services.budget import transfer_rules as service

if TYPE_CHECKING:
    from app.models.transfer_rule import TransferRule

router = APIRouter(prefix="/transfer-rules", tags=["transfer-rules"])


@router.get("", response_model=list[TransferRuleRead])
def list_rules(db: Session = Depends(get_db)) -> "list[TransferRule]":
    return service.list_rules(db)


@router.post("", response_model=TransferRuleRead, status_code=201)
def create_rule(payload: TransferRuleCreate, db: Session = Depends(get_db)) -> "TransferRule":
    return service.create_rule(db, payload)


@router.patch("/{rule_id}", response_model=TransferRuleRead)
def update_rule(rule_id: int, payload: TransferRuleUpdate, db: Session = Depends(get_db)) -> "TransferRule":
    return service.update_rule(db, rule_id, payload)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)) -> None:
    service.delete_rule(db, rule_id)


@router.post("/apply", response_model=TransferApplyResult)
def apply_transfer_rules(
    dry_run: bool = Query(default=False),
    rule_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> TransferApplyResult:
    """Rattrape tout l'historique avec les règles actives. `dry_run=true` : aperçu sans écriture."""
    return run_async(service.apply_transfer_rules(db, dry_run, rule_id))
