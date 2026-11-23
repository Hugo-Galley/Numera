"""Hausses de prix des abonnements."""
from app.core.i18n import format_currency, format_date, format_number, tr
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
            "audit.subscription_prices.description",
            old=format_currency(change.old_amount, change.currency), new=format_currency(change.new_amount, change.currency),
            period=tr(_PERIOD_KEYS.get(change.frequency, "audit.period.other")),
            date=format_date(change.changed_on), delta=("+" if change.delta_pct >= 0 else "") + format_number(change.delta_pct, 1),
            impact=format_currency(change.annual_impact, change.currency),
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
