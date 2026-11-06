"""Aides perçues : déclaration à faire, versement manquant, montant modifié."""
from app.core.i18n import tr
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
        title=tr("audit.benefits.declaration_late" if overdue else "audit.benefits.declaration_due", organization=b.organization),
        description=tr("audit.benefits.declaration_description", name=b.name, due=due),
        action_label=tr("audit.benefits.action"),
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
        title=tr("audit.benefits.late_title", name=b.name),
        description=tr(
            "audit.benefits.late_description", pattern=b.match_pattern,
            date=st.expected_date.strftime("%d/%m/%Y"), organization=b.organization,
        ),
        action_label=tr("audit.benefits.action"),
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
        title=tr("audit.benefits.amount_title", name=b.name),
        description=tr(
            "audit.benefits.amount_description", received=f"{last.amount:.2f}",
            date=last.date.strftime("%d/%m/%Y"), expected=f"{b.amount:.2f}",
        ),
        action_label=tr("audit.benefits.action"),
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
