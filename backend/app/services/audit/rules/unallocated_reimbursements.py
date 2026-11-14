"""Remboursements reçus non affectés à une créance ouverte."""
from app.core.i18n import tr, trn
from app.domain.transactions import tx_sample
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext, unallocated_reimbursements_query


def detect(ctx: AuditContext) -> list[ActionItem]:
    query = unallocated_reimbursements_query(ctx.db, ctx.now)
    if query is None:
        return []
    count = query.count()
    if not count:
        return []
    return [ActionItem(
        id="unallocated-reimbursements",
        type="audit",
        severity="low",
        title=tr("audit.unallocated_reimbursements.title"),
        description=trn("audit.unallocated_reimbursements.description", count),
        action_label=tr("audit.unallocated_reimbursements.action"),
        action_url="/reimbursements",
        action_type="link",
        samples=[tx_sample(tx) for tx in query.limit(5).all()],
        metadata={"issue_id": "unallocated-reimbursements"}
    )]
