"""Hausses de prix des abonnements."""
from app.core.i18n import tr
from app.domain.subscription_prices import price_change_id
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext
from app.services.budget.subscription_prices import detect_price_changes

_PERIOD_KEYS = {"monthly": "audit.period.monthly", "quarterly": "audit.period.quarterly", "yearly": "audit.period.yearly"}


def detect(ctx: AuditContext) -> list[ActionItem]:
    return [ActionItem(
        id=price_change_id(change),
        type="subscription",
        severity="medium",
        title=tr("audit.subscription_prices.title", name=change.name),
        description=tr(
            "audit.subscription_prices.description", old=f"{change.old_amount:.2f}", new=f"{change.new_amount:.2f}",
            currency=change.currency, period=tr(_PERIOD_KEYS.get(change.frequency, "audit.period.other")),
            date=change.changed_on.strftime("%d/%m/%Y"), delta=f"{change.delta_pct:+.1f}",
            impact=f"{change.annual_impact:.2f}",
        ),
        action_label=tr("audit.subscription_prices.action"),
        action_url="/recurring?tab=subscriptions",
        action_type="link",
        metadata={
            "account_id": change.account_id,
            "old_amount": change.old_amount,
            "new_amount": change.new_amount,
            "annual_impact": change.annual_impact,
        },
    ) for change in detect_price_changes(ctx.db)]
