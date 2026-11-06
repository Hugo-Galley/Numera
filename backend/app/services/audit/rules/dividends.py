"""Dividendes des comptes titres : non rattachés à un titre, ou attendus et absents depuis 13 mois."""
from datetime import timedelta

from app.core.i18n import tr, trn
from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def detect(ctx: AuditContext) -> list[ActionItem]:
    account_names = repo.account_names(ctx.db)
    actions = [ActionItem(
        id=f"dividends-unlinked-{acc_id}",
        type="investments",
        severity="medium",
        title=tr("audit.dividends.unlinked_title", account=account_names.get(acc_id, acc_id)),
        description=trn("audit.dividends.unlinked_description", count),
        action_label=tr("audit.dividends.unlinked_action"),
        action_url=f"/accounts/{acc_id}",
        action_type="link",
        metadata={"account_id": acc_id, "count": count},
    ) for acc_id, count in repo.unlinked_dividend_counts(ctx.db)]
    return actions + _missing_dividends(ctx)


def _missing_dividends(ctx: AuditContext) -> list[ActionItem]:
    """Titre distribuant sans dividende depuis plus de 13 mois (réglage manuel, aucun appel externe)."""
    stale_before = ctx.now - timedelta(days=395)
    last_dividend = repo.last_dividend_by_ticker(ctx.db)
    actions = []
    for h in repo.dividend_paying_holdings(ctx.db):
        reference = last_dividend.get((h.account_id, h.ticker.upper())) or h.created_at
        if reference < stale_before:
            actions.append(ActionItem(
                id=f"dividend-missing-{h.account_id}-{h.ticker}",
                type="investments",
                severity="low",
                title=tr("audit.dividends.missing_title", name=h.asset_name),
                description=tr("audit.dividends.missing_description", ticker=h.ticker),
                action_label=tr("audit.dividends.missing_action"),
                action_url=f"/accounts/{h.account_id}",
                action_type="link",
                metadata={"account_id": h.account_id, "ticker": h.ticker},
            ))
    return actions
