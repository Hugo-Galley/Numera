"""Hausses de prix des abonnements."""
from app.domain.subscription_prices import price_change_id
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext
from app.services.subscription_prices import detect_price_changes

FREQ_LABEL = {"monthly": "mois", "quarterly": "trimestre", "yearly": "an"}


def detect(ctx: AuditContext) -> list[ActionItem]:
    return [ActionItem(
        id=price_change_id(change),
        type="subscription",
        severity="medium",
        title=f"Hausse de prix : {change.name}",
        description=(
            f"Passé de {change.old_amount:.2f} à {change.new_amount:.2f} {change.currency} "
            f"par {FREQ_LABEL.get(change.frequency, 'échéance')} le {change.changed_on.strftime('%d/%m/%Y')} "
            f"({change.delta_pct:+.1f} %), soit {change.annual_impact:.2f} {change.currency} de plus par an. "
            "Toujours utile à ce prix ?"
        ),
        action_label="Voir les abonnements",
        action_url="/recurring?tab=subscriptions",
        action_type="link",
        metadata={
            "account_id": change.account_id,
            "old_amount": change.old_amount,
            "new_amount": change.new_amount,
            "annual_impact": change.annual_impact,
        },
    ) for change in detect_price_changes(ctx.db)]
