"""Aides perçues : déclaration à faire, versement manquant, montant modifié."""
from app.domain.benefits import amount_changed
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext
from app.services.budget.benefits import BenefitState, compute_states

# Rappel de la déclaration périodique, en jours avant l'échéance
DECLARATION_REMINDER_DAYS = 7
URL = "/recurring?tab=salary&vue=aides"


def _declaration(st: BenefitState) -> ActionItem | None:
    b = st.benefit
    if st.declaration_days_left is None or st.declaration_days_left > DECLARATION_REMINDER_DAYS:
        return None
    overdue = st.declaration_days_left < 0
    due = b.next_declaration_date.strftime("%d/%m/%Y")
    return ActionItem(
        id=f"benefit-declaration-{b.id}-{b.next_declaration_date.isoformat()}",
        type="audit",
        severity="high" if overdue else "medium",
        title=f"Déclaration {b.organization} en retard" if overdue else f"Déclaration {b.organization} à faire",
        description=(
            f"{b.name} : déclaration attendue le {due}. Sans elle, le versement peut être suspendu. "
            "Marque-la comme faite une fois envoyée."
        ),
        action_label="Ouvrir les aides",
        action_url=URL,
        action_type="link",
        metadata={"benefit_id": b.id, "due_date": b.next_declaration_date.isoformat()},
    )


def _late(st: BenefitState) -> ActionItem | None:
    if st.status != "late":
        return None
    b = st.benefit
    return ActionItem(
        id=f"benefit-late-{b.id}-{st.expected_date.strftime('%Y-%m')}",
        type="audit",
        severity="medium",
        title=f"{b.name} non reçue",
        description=(
            f"Aucun versement « {b.match_pattern} » depuis le {st.expected_date.strftime('%d/%m/%Y')}. "
            f"Vérifie ton espace {b.organization} ou importe tes derniers relevés."
        ),
        action_label="Ouvrir les aides",
        action_url=URL,
        action_type="link",
        metadata={"benefit_id": b.id},
    )


def _amount_changed(st: BenefitState) -> ActionItem | None:
    if not st.payments:
        return None
    b, last = st.benefit, st.payments[0]
    if not amount_changed(b.amount, last.amount):
        return None
    return ActionItem(
        id=f"benefit-amount-{b.id}-{last.date.date().isoformat()}",
        type="audit",
        severity="low",
        title=f"{b.name} : montant modifié",
        description=f"Reçu {last.amount:.2f} le {last.date.strftime('%d/%m/%Y')} pour {b.amount:.2f} attendus. Mets à jour le montant si c'est le nouveau droit.",
        action_label="Ouvrir les aides",
        action_url=URL,
        action_type="link",
        metadata={"benefit_id": b.id, "received": last.amount, "expected": b.amount},
    )


def detect(ctx: AuditContext) -> list[ActionItem]:
    actions: list[ActionItem] = []
    for st in compute_states(ctx.db, ctx.now.date()):
        if not st.benefit.active:
            continue
        actions.extend(a for a in (_declaration(st), _late(st), _amount_changed(st)) if a is not None)
    return actions
