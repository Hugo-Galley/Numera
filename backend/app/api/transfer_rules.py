from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.transfers import Pair, apply_rules
from app.models.account import Account
from app.models.transfer_rule import TransferRule
from app.schemas.transfer_rule import (
    TransferApplyResult,
    TransferLegPreview,
    TransferPairPreview,
    TransferRuleCreate,
    TransferRuleRead,
    TransferRuleUpdate,
)

router = APIRouter(prefix="/transfer-rules", tags=["transfer-rules"])


def _check_accounts(db: Session, source_id: int, dest_id: int) -> None:
    if source_id == dest_id:
        raise HTTPException(status_code=422, detail="Source and destination accounts must differ")
    found = {a.id for a in db.query(Account.id).filter(Account.id.in_([source_id, dest_id])).all()}
    if {source_id, dest_id} - found:
        raise HTTPException(status_code=404, detail="Account not found")


def _preview(pair: Pair) -> TransferPairPreview:
    return TransferPairPreview(
        rule_id=pair.rule_id,
        kind=pair.kind,
        day_gap=pair.day_gap,
        sortie=TransferLegPreview(
            id=pair.sortie.id, account_id=pair.sortie.account_id, date=pair.sortie.date,
            amount=pair.sortie.amount, currency=pair.sortie.currency, label=pair.sortie.merchant,
        ),
        entree=TransferLegPreview(
            id=pair.entree.id, account_id=pair.entree.account_id, date=pair.entree.date,
            amount=pair.entree.amount, currency=pair.entree.currency,
            label=getattr(pair.entree, "merchant", None) or getattr(pair.entree, "note", None),
        ),
    )


@router.get("", response_model=list[TransferRuleRead])
def list_rules(db: Session = Depends(get_db)):
    return db.query(TransferRule).order_by(TransferRule.id).all()


@router.post("", response_model=TransferRuleRead, status_code=201)
def create_rule(payload: TransferRuleCreate, db: Session = Depends(get_db)):
    _check_accounts(db, payload.source_account_id, payload.dest_account_id)
    rule = TransferRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=TransferRuleRead)
def update_rule(rule_id: int, payload: TransferRuleUpdate, db: Session = Depends(get_db)):
    rule = db.get(TransferRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    data = payload.model_dump(exclude_unset=True)
    _check_accounts(
        db,
        data.get("source_account_id", rule.source_account_id),
        data.get("dest_account_id", rule.dest_account_id),
    )
    for key, value in data.items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(TransferRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return


@router.post("/apply", response_model=TransferApplyResult)
async def apply_transfer_rules(
    dry_run: bool = Query(default=False),
    rule_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Rattrape tout l'historique avec les règles actives. `dry_run=true` : aperçu sans écriture."""
    pairs = await apply_rules(db, rule_ids=[rule_id] if rule_id else None, dry_run=dry_run)
    return TransferApplyResult(dry_run=dry_run, count=len(pairs), pairs=[_preview(p) for p in pairs])
