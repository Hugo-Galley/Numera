"""Sauvegardes en retard ou en échec (seulement si elles sont en place)."""
from app.integrations.backup import backup_status
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def detect(ctx: AuditContext) -> list[ActionItem]:
    backup = backup_status()
    if not (backup["configured"] and (backup["stale"] or backup["last_error"])):
        return []
    last = backup["last_backup_at"]
    when = last.astimezone().strftime("%d/%m/%Y") if last else "jamais"
    description = (
        f"Dernière sauvegarde réussie : {when}."
        + (f" Dernière erreur : {backup['last_error']}" if backup["last_error"] else "")
    )
    return [ActionItem(
        # L'id change avec la dernière sauvegarde : masquer l'alerte ne la fait pas taire pour toujours
        id=f"backup-failing-{last.strftime('%Y%m%d') if last else 'never'}",
        type="audit",
        severity="high",
        title="Sauvegarde en retard" if backup["stale"] else "Dernière sauvegarde en échec",
        description=description,
        action_label="Voir les sauvegardes",
        action_url="/settings?tab=data",
        action_type="link",
    )]
