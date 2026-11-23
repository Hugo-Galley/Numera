"""Plafonds de budget dépassés ou presque atteints sur le mois en cours."""
from app.core.i18n import format_money, tr
from app.schemas.insight import ActionItem
from app.services.analytics.budget import compute_budget_alerts
from app.services.audit.context import AuditContext


async def detect(ctx: AuditContext) -> list[ActionItem]:
    alerts = await compute_budget_alerts(year=ctx.now.year, month=ctx.now.month, account_id=None, db=ctx.db)
    over_budget = [a for a in alerts if a.monthly_ratio and a.monthly_ratio >= 1.0]
    near_budget = [a for a in alerts if a.monthly_ratio and a.monthly_ratio >= 0.85 and a.monthly_ratio < 1.0]
    actions = [ActionItem(
        id=f"budget-over-{alert.category_id}",
        type="budget",
        severity="high",
        title=tr("audit.budget.over_title", category=alert.category_name),
        description=tr("audit.budget.over_description", spent=format_money(alert.monthly_spent), limit=format_money(alert.monthly_limit or 0.0)),
        action_label=tr("audit.budget.over_action"),
        action_url="/accounts",  # Could be a specific category view if it existed
        action_type="link",
        metadata={"category_id": alert.category_id, "spent": alert.monthly_spent, "limit": alert.monthly_limit}
    ) for alert in over_budget]
    actions += [ActionItem(
        id=f"budget-near-{alert.category_id}",
        type="budget",
        severity="medium",
        title=tr("audit.budget.near_title", category=alert.category_name),
        description=tr("audit.budget.near_description", pct=round((alert.monthly_ratio or 0.0) * 100), category=alert.category_name),
        action_label=tr("audit.budget.near_action"),
        action_url="/accounts",
        action_type="link",
        metadata={"category_id": alert.category_id, "spent": alert.monthly_spent, "limit": alert.monthly_limit}
    ) for alert in near_budget]
    return actions
