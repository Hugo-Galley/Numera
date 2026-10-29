"""Virements internes potentiels non rapprochés (contrôle simplifié sur 90 jours)."""
from datetime import timedelta

from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def detect(ctx: AuditContext) -> list[ActionItem]:
    sorties = repo.recent_unlinked_sorties(ctx.db, ctx.now - timedelta(days=90), strict=False, limit=100)
    count = sum(1 for sortie in sorties if repo.transfer_match(ctx.db, sortie))
    if not count:
        return []
    return [ActionItem(
        id="possible-transfers",
        type="audit",
        severity="medium",
        title="Transferts non rapprochés",
        description=f"{count} virements internes potentiels ont été détectés.",
        action_label="Rapprocher",
        action_url="/audit?vue=virements",
        action_type="link",
        metadata={"issue_id": "unmatched-transfers"}
    )]
