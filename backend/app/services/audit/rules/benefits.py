"""Aides perçues : déclaration à faire, versement manquant, montant modifié."""
from app.core.i18n import format_date, format_money, tr
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
    due_date = b.next_declaration_date
    if due_date is None:
        return None
    overdue = st.declaration_days_left < 0
    due = format_date(due_date)
    return ActionItem(
        id=f"benefit-declaration-{b.id}-{due_date.isoformat()}",
        type="audit",
        severity="high" if overdue else "medium",
        title=tr("audit.benefits.declaration_late" if overdue else "audit.benefits.declaration_due", organization=b.organization),
        description=tr("audit.benefits.declaration_description", name=b.name, due=due),
        action_label=tr("audit.benefits.action"),
        action_url=URL,
        action_type="link",
        metadata={"benefit_id": b.id, "due_date": due_date.isoformat()},
    )


def _late(st: BenefitState) -> ActionItem | None:
    if st.status != "late":
        return None
    b = st.benefit
    expected = st.expected_date
    if expected is None:
        return None
    return ActionItem(
        id=f"benefit-late-{b.id}-{expected.strftime('%Y-%m')}",
        type="audit",
        severity="medium",
        title=tr("audit.benefits.late_title", name=b.name),
        description=tr(
            "audit.benefits.late_description", pattern=b.match_pattern,
            date=format_date(expected), organization=b.organization,
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
            "audit.benefits.amount_description", received=format_money(last.amount),
            date=format_date(last.date), expected=format_money(b.amount),
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
