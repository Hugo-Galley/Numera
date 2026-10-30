"""Centre d'Actions : registre de règles (une par module de `rules/`) et audit des données.

Ajouter une action : créer `rules/<nom>.py` exposant `detect(ctx) -> list[ActionItem]` (ou `async def`),
puis l'ajouter à `RULES`. Une règle en échec est journalisée et ignorée, les autres s'affichent.
"""
import inspect
from collections.abc import Callable
from datetime import datetime
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.core.errors import InternalError
from app.core.logging import get_logger
from app.domain.audit import SEVERITY_ORDER
from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionCenterResponse, ActionCenterSummary, ActionItem
from app.services.audit.context import AuditContext, unallocated_reimbursements_query
from app.services.audit.data_audit import compute_data_audit, compute_data_audit_issue
from app.services.audit.rules import (
    backups,
    benefits,
    broker_reconciliation,
    budget,
    dividends,
    duplicates,
    merchant_suggestions,
    missing_salary,
    missing_snapshots,
    rule_suggestions,
    subscription_prices,
    unallocated_reimbursements,
    uncategorized,
    unmatched_transfers,
)

logger = get_logger(__name__)


class Rule(NamedTuple):
    name: str
    detect: Callable


RULES: list[Rule] = [
    Rule("uncategorized", uncategorized.detect),
    Rule("duplicates", duplicates.detect),
    Rule("missing_snapshots", missing_snapshots.detect),
    Rule("missing_salary", missing_salary.detect),
    Rule("benefits", benefits.detect),
    Rule("unmatched_transfers", unmatched_transfers.detect),
    Rule("unallocated_reimbursements", unallocated_reimbursements.detect),
    Rule("budget", budget.detect),
    Rule("rule_suggestions", rule_suggestions.detect),
    Rule("merchant_suggestions", merchant_suggestions.detect),
    Rule("dividends", dividends.detect),
    Rule("broker_reconciliation", broker_reconciliation.detect),
    Rule("subscription_prices", subscription_prices.detect),
    Rule("backups", backups.detect),
]


async def compute_action_center(db: Session) -> ActionCenterResponse:
    try:
        ctx = AuditContext(db=db, now=datetime.now())
        actions: list[ActionItem] = []
        for rule in RULES:
            try:
                found = rule.detect(ctx)
                actions.extend(await found if inspect.isawaitable(found) else found)
            except Exception as exc:  # une règle d'audit ne doit jamais casser le Centre d'Actions
                logger.warning(f"Règle d'audit « {rule.name} » ignorée : {exc}")
        return _summary(db, ctx.now, actions)
    except Exception as e:
        logger.error(f"Error in get_action_center: {e}", exc_info=True)
        raise InternalError(str(e)) from e


def _summary(db: Session, now: datetime, actions: list[ActionItem]) -> ActionCenterResponse:
    # Safe sort: defaults to 3 (lowest) if severity is unexpected
    actions.sort(key=lambda x: SEVERITY_ORDER.get(x.severity, 3))
    dismissed = repo.dismissed_ids(db)
    actions = [a for a in actions if a.id not in dismissed]
    return ActionCenterResponse(
        summary=ActionCenterSummary(
            total_actions=len(actions),
            high_priority=sum(1 for a in actions if a.severity == "high"),
            medium_priority=sum(1 for a in actions if a.severity == "medium"),
            low_priority=sum(1 for a in actions if a.severity == "low"),
            checked_at=now.isoformat()
        ),
        actions=actions
    )


def dismiss_action(db: Session, action_id: str) -> dict:
    if not repo.is_dismissed(db, action_id):
        repo.add_dismissed(db, action_id)
        db.commit()
    return {"status": "success"}


__all__ = [
    "RULES",
    "Rule",
    "compute_action_center",
    "compute_data_audit",
    "compute_data_audit_issue",
    "dismiss_action",
    "unallocated_reimbursements_query",
]
