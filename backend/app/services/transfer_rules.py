from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.domain.transfers import Pair
from app.models.transfer_rule import TransferRule
from app.repositories import transfer_rules as repo
from app.schemas.transfer_rule import (
    TransferApplyResult,
    TransferLegPreview,
    TransferPairPreview,
    TransferRuleCreate,
    TransferRuleUpdate,
)
from app.services.transfers import apply_rules


def _check_accounts(db: Session, source_id: int, dest_id: int) -> None:
    if source_id == dest_id:
        raise BusinessRuleError("Source and destination accounts must differ")
    if {source_id, dest_id} - repo.existing_account_ids(db, [source_id, dest_id]):
        raise NotFoundError("Account not found")


def _require(db: Session, rule_id: int) -> TransferRule:
    rule = repo.get(db, rule_id)
    if not rule:
        raise NotFoundError("Rule not found")
    return rule


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


def list_rules(db: Session) -> list[TransferRule]:
    return repo.list_all(db)


def create_rule(db: Session, payload: TransferRuleCreate) -> TransferRule:
    _check_accounts(db, payload.source_account_id, payload.dest_account_id)
    rule = TransferRule(**payload.model_dump())
    repo.add(db, rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, rule_id: int, payload: TransferRuleUpdate) -> TransferRule:
    rule = _require(db, rule_id)
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


def delete_rule(db: Session, rule_id: int) -> None:
    repo.delete(db, _require(db, rule_id))
    db.commit()


async def apply_transfer_rules(db: Session, dry_run: bool, rule_id: int | None) -> TransferApplyResult:
    """Rattrape tout l'historique avec les règles actives. `dry_run=True` : aperçu sans écriture."""
    pairs = await apply_rules(db, rule_ids=[rule_id] if rule_id else None, dry_run=dry_run)
    return TransferApplyResult(dry_run=dry_run, count=len(pairs), pairs=[_preview(p) for p in pairs])
