"""Comptes d'investissement sans relevé depuis plus de 45 jours."""
from app.core.i18n import tr, trn
from app.repositories.analytics import audit as repo
from app.repositories.comptes import balances
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def detect(ctx: AuditContext) -> list[ActionItem]:
    stale = []
    for account in balances.active_accounts(ctx.db):
        if account.type != "investissement":
            continue
        last = repo.latest_snapshot_date(ctx.db, account.id)
        if not last or (ctx.now - last).days > 45:
            stale.append(account)
    if not stale:
        return []
    return [ActionItem(
        id="stale-snapshots",
        type="audit",
        severity="medium",
        title=tr("audit.stale_snapshots.title"),
        description=trn("audit.stale_snapshots.description", len(stale)),
        action_label=tr("audit.stale_snapshots.action"),
        action_url="/investments",
        action_type="link",
        metadata={"account_ids": [acc.id for acc in stale]}
    )]
