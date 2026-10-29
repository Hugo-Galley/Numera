"""Règles de catégorisation suggérées.

Une règle ne s'applique qu'à l'import (et via « appliquer à tout ») : elle n'apporte quelque chose
que si le marchand a encore des transactions sans catégorie. Virements et récurrences (qui portent
leur propre catégorie) ne comptent pas.
"""
from datetime import timedelta

from app.repositories.analytics import audit as repo
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def _stats_by_merchant(rows: list) -> dict[str, dict]:
    by_merchant: dict[str, dict] = {}
    for merchant, category_id, count in rows:
        stats = by_merchant.setdefault(merchant, {"total": 0, "uncategorized": 0, "categories": {}})
        stats["total"] += count
        if category_id is None:
            stats["uncategorized"] += count
        else:
            stats["categories"][category_id] = stats["categories"].get(category_id, 0) + count
    return by_merchant


def detect(ctx: AuditContext) -> list[ActionItem]:
    by_merchant = _stats_by_merchant(repo.merchant_category_counts(ctx.db, ctx.now - timedelta(days=180)))
    actions = []
    for merchant, stats in sorted(by_merchant.items(), key=lambda kv: -kv[1]["uncategorized"]):
        if stats["total"] < 5 or stats["uncategorized"] == 0:
            continue
        if repo.rule_exists(ctx.db, merchant):
            continue
        suggested_cat_id = max(stats["categories"], key=stats["categories"].get) if stats["categories"] else None
        actions.append(ActionItem(
            id=f"suggest-rule-{merchant}",
            type="rule",
            severity="low",
            title=f"Nouvelle règle suggérée : {merchant}",
            description=(
                f"{stats['uncategorized']} transaction(s) sans catégorie chez '{merchant}' "
                f"(sur {stats['total']}). Une règle les catégoriserait, ainsi que les prochains imports."
            ),
            action_label="Créer la règle",
            action_url="/classement?tab=rules",
            action_type="modal_rule",
            metadata={"merchant": merchant, "suggested_category_id": suggested_cat_id}
        ))
    return actions
