"""Rapprochement : dernier relevé du courtier vs valeur calculée par Numera."""
from app.core.i18n import tr
from app.core.logging import get_logger
from app.domain.portfolio import RECONCILIATION_THRESHOLD_PCT, uses_positions
from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext
from app.services.investissement.holdings.replay import replay_account
from app.services.investissement.portfolio import compute_portfolio

logger = get_logger(__name__)


async def detect(ctx: AuditContext) -> list[ActionItem]:
    actions = []
    for account in repo.active_investment_accounts(ctx.db):
        try:
            if not uses_positions(account, await replay_account(ctx.db, account.id)):
                continue
            portfolio = await compute_portfolio(ctx.db, account, fetch=False)
        except Exception as exc:  # une règle d'audit ne doit jamais casser le Centre d'Actions
            logger.warning(f"Reconciliation skipped for account {account.id}: {exc}")
            continue
        latest = (portfolio["reconciliation"] or [None])[-1]
        if latest and latest["flagged"]:
            actions.append(ActionItem(
                id=f"reconciliation-gap-{account.id}-{latest['date'][:10]}",
                type="investments",
                severity="medium",
                title=tr("audit.broker_reconciliation.title", account=account.name),
                description=tr(
                    "audit.broker_reconciliation.description", date=latest["date"][:10], currency=account.currency,
                    snapshot=f"{latest['snapshot_value']:.2f}", computed=f"{latest['computed_value']:.2f}",
                    gap=f"{latest['gap_pct']:+.1f}", threshold=f"{RECONCILIATION_THRESHOLD_PCT:.0f}",
                ),
                action_label=tr("audit.broker_reconciliation.action"),
                action_url=f"/accounts/{account.id}",
                action_type="link",
                metadata={"account_id": account.id, **latest},
            ))
    return actions
