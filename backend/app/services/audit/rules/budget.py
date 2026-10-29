"""Plafonds de budget dépassés ou presque atteints sur le mois en cours."""
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
        title=f"Budget dépassé : {alert.category_name}",
        description=f"Vous avez dépensé {round(alert.monthly_spent, 2)}€ pour une limite de {alert.monthly_limit}€.",
        action_label="Voir détails",
        action_url="/accounts",  # Could be a specific category view if it existed
        action_type="link",
        metadata={"category_id": alert.category_id, "spent": alert.monthly_spent, "limit": alert.monthly_limit}
    ) for alert in over_budget]
    actions += [ActionItem(
        id=f"budget-near-{alert.category_id}",
        type="budget",
        severity="medium",
        title=f"Budget presque atteint : {alert.category_name}",
        description=f"Vous êtes à {round(alert.monthly_ratio * 100)}% de votre limite pour {alert.category_name}.",
        action_label="Surveiller",
        action_url="/accounts",
        action_type="link",
        metadata={"category_id": alert.category_id, "spent": alert.monthly_spent, "limit": alert.monthly_limit}
    ) for alert in near_budget]
    return actions
