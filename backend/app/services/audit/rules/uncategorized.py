"""Dépenses sans catégorie."""
from app.core.i18n import tr, trn
from app.domain.transactions import tx_sample
from app.models.transaction import Transaction
from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def detect(ctx: AuditContext) -> list[ActionItem]:
    query = repo.uncategorized_expenses(ctx.db).order_by(Transaction.date.desc())
    count = query.count()
    if not count:
        return []
    return [ActionItem(
        id="uncategorized-expenses",
        type="audit",
        severity="high",
        title=tr("audit.uncategorized.title"),
        description=trn("audit.uncategorized.description", count),
        action_label=tr("audit.uncategorized.action"),
        action_url="/audit",  # Pointing to the audit/actions page
        action_type="modal_categorize",
        samples=[tx_sample(tx) for tx in query.limit(5).all()],
        metadata={"issue_id": "uncategorized-expenses"}
    )]
