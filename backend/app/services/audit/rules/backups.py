"""Sauvegardes en retard ou en échec (seulement si elles sont en place)."""
from app.core.i18n import tr
from app.integrations.backup import backup_status
from app.schemas.insight import ActionItem
from app.services.audit.context import AuditContext


def detect(ctx: AuditContext) -> list[ActionItem]:
    backup = backup_status()
    if not (backup["configured"] and (backup["stale"] or backup["last_error"])):
        return []
    last = backup["last_backup_at"]
    when = last.astimezone().strftime("%d/%m/%Y") if last else tr("audit.backups.never")
    description = tr("audit.backups.description", when=when) + (
        tr("audit.backups.last_error", error=backup["last_error"]) if backup["last_error"] else ""
    )
    return [ActionItem(
        # L'id change avec la dernière sauvegarde : masquer l'alerte ne la fait pas taire pour toujours
        id=f"backup-failing-{last.strftime('%Y%m%d') if last else 'never'}",
        type="audit",
        severity="high",
        title=tr("audit.backups.late_title") if backup["stale"] else tr("audit.backups.failed_title"),
        description=description,
        action_label=tr("audit.backups.action"),
        action_url="/settings?tab=data",
        action_type="link",
    )]
