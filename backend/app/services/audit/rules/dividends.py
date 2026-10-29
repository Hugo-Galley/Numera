"""Dividendes des comptes titres : non rattachés à un titre, ou attendus et absents depuis 13 mois."""
from datetime import timedelta

from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def detect(ctx: AuditContext) -> list[ActionItem]:
    account_names = repo.account_names(ctx.db)
    actions = [ActionItem(
        id=f"dividends-unlinked-{acc_id}",
        type="investments",
        severity="medium",
        title=f"Dividendes à rattacher à un titre : {account_names.get(acc_id, acc_id)}",
        description=f"{count} dividende(s) ne sont rattachés à aucun titre : rendement et plus-value totale par ligne sont incomplets.",
        action_label="Rattacher",
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
                title=f"Dividende attendu : {h.asset_name}",
                description=f"Aucun dividende saisi sur {h.ticker} depuis plus de 13 mois. En as-tu reçu un ?",
                action_label="Saisir un dividende",
                action_url=f"/accounts/{h.account_id}",
                action_type="link",
                metadata={"account_id": h.account_id, "ticker": h.ticker},
            ))
    return actions
