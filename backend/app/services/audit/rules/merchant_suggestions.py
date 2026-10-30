"""Normalisation de marchands suggérée.

Un marchand canonique sert à regrouper plusieurs écritures d'un même commerçant : on ne le propose
que si le même nom apparaît sous au moins deux libellés (casse, accents, chiffres, ponctuation).
"""
from app.domain.audit import merchant_variants
from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def detect(ctx: AuditContext) -> list[ActionItem]:
    actions = []
    for labels in merchant_variants(repo.unnormalized_merchant_counts(ctx.db).all())[:5]:
        main_label, _ = labels[0]
        total = sum(c for _, c in labels)
        actions.append(ActionItem(
            id=f"suggest-normalization-{main_label}",
            type="merchant",
            severity="low",
            title=f"Normalisation suggérée : {main_label}",
            description=(
                f"{len(labels)} écritures pour le même marchand ({', '.join(repr(label) for label, _ in labels[:4])}), "
                f"{total} transactions. Les regrouper sous un marchand canonique ?"
            ),
            action_label="Normaliser",
            action_url="/classement?tab=merchants",
            action_type="modal_merchant",
            metadata={"merchant": main_label, "count": total, "variants": [label for label, _ in labels]}
        ))
    return actions
