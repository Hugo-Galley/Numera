"""Virements internes potentiels non rapprochés (contrôle simplifié sur 90 jours)."""
from datetime import timedelta

from app.domain.transfers import strict_matches
from app.models.transaction import Transaction
from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def detect(ctx: AuditContext) -> list[ActionItem]:
    sorties = repo.recent_unlinked_sorties(ctx.db, ctx.now - timedelta(days=90), strict=True, limit=100)
    # Candidats chargés en une requête pour tout le lot, appariement en mémoire (comme l'audit des données)
    entrees: dict[float, list[Transaction]] = {}
    for entree in repo.strict_transfer_candidates(ctx.db, sorties):
        entrees.setdefault(entree.amount, []).append(entree)
    count = sum(1 for sortie in sorties if strict_matches(sortie, entrees))
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
