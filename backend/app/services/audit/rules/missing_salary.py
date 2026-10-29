"""Salaire attendu absent (mois non renseigné dans le gestionnaire de salaire)."""
from app.domain.audit import month_name
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext
from app.services.budget.salary_generation import find_missing_salary_months


def detect(ctx: AuditContext) -> list[ActionItem]:
    months = find_missing_salary_months(ctx.db, ctx.now.date())
    if not months:
        return []
    labels = ", ".join(month_name(label) for label in months)
    return [ActionItem(
        id=f"missing-salary-{months[-1]}",
        type="audit",
        severity="high",
        title="Salaire absent",
        description=(
            f"Aucun salaire pour {labels}. Renseigne le mois dans le gestionnaire de salaire, "
            "ou désactive la configuration si tu ne perçois plus ce salaire."
        ),
        action_label="Ouvrir le salaire",
        action_url="/recurring?tab=salary",
        action_type="link",
        metadata={"months": months},
    )]
