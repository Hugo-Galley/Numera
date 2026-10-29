"""Rapprochement : dernier relevé du courtier vs valeur calculée par Numera."""
from app.core.holdings import replay_account
from app.core.logging import get_logger
from app.core.portfolio import RECONCILIATION_THRESHOLD_PCT, compute_portfolio, uses_positions
from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext

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
                title=f"Écart avec le relevé du courtier : {account.name}",
                description=(
                    f"Le relevé du {latest['date'][:10]} indique {latest['snapshot_value']:.2f} {account.currency}, "
                    f"Numera calcule {latest['computed_value']:.2f} ({latest['gap_pct']:+.1f} %, seuil {RECONCILIATION_THRESHOLD_PCT:.0f} %). "
                    "Une opération, des frais ou un dividende manquent probablement."
                ),
                action_label="Vérifier le compte",
                action_url=f"/accounts/{account.id}",
                action_type="link",
                metadata={"account_id": account.id, **latest},
            ))
    return actions
