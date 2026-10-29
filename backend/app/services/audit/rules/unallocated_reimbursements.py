"""Remboursements reçus non affectés à une créance ouverte."""
from app.domain.transactions import tx_sample
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext, unallocated_reimbursements_query


def detect(ctx: AuditContext) -> list[ActionItem]:
    query = unallocated_reimbursements_query(ctx.db, ctx.now)
    count = query.count() if query is not None else 0
    if not count:
        return []
    return [ActionItem(
        id="unallocated-reimbursements",
        type="audit",
        severity="low",
        title="Remboursements à affecter",
        description=f"{count} remboursement(s) reçu(s) ne sont rattachés à aucune créance ouverte.",
        action_label="Affecter",
        action_url="/reimbursements",
        action_type="link",
        samples=[tx_sample(tx) for tx in query.limit(5).all()],
        metadata={"issue_id": "unallocated-reimbursements"}
    )]
