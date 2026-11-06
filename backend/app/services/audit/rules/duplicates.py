"""Doublons suspects (même compte, date, type, marchand, montant et devise)."""
from app.core.i18n import tr
from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def detect(ctx: AuditContext) -> list[ActionItem]:
    groups = repo.duplicate_groups(ctx.db).all()
    if not groups:
        return []
    count = sum(int(row.count) for row in groups)
    return [ActionItem(
        id="duplicate-transactions",
        type="audit",
        severity="high",
        title=tr("audit.duplicates.title"),
        description=tr("audit.duplicates.description", count=count),
        action_label=tr("audit.duplicates.action"),
        action_url="/audit",
        action_type="modal_categorize",  # Reusing the detail modal logic
        metadata={"issue_id": "duplicate-transactions"}
    )]
