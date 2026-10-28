"""Instantané cohérent de la base SQLite (API de backup, valable aussi en mode WAL)."""
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def snapshot_database(db_path: str, dest_dir: Path | str, prefix: str = "snapshot") -> Path:
    """Copie `db_path` dans `dest_dir/<prefix>_<horodatage>.db` et vérifie son intégrité."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    try:
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
            result = target.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            target.close()
    finally:
        source.close()
    if result != "ok":
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"Instantané invalide : {result}")
    return dest


# --- État des sauvegardes (Paramètres → Données, Centre d'actions) ---

# Le conteneur `backup` tourne toutes les 24 h : au-delà de 2 jours, une sauvegarde a été manquée
BACKUP_STALE_AFTER = timedelta(days=2)


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def backup_status(now: datetime | None = None) -> dict:
    """État des sauvegardes, lu dans BACKUP_DIR (fichiers `suivi_budget_*` et `status.json` écrit par scripts/backup.py)."""
    now = now or datetime.now(timezone.utc)
    backup_dir = Path(os.getenv("BACKUP_DIR", "/app/backups"))
    github_configured = bool(os.getenv("GITHUB_BACKUP_REPO", "").strip())
    files = (
        sorted(
            (p for p in backup_dir.glob("suivi_budget_*") if p.is_file() and not p.name.endswith(".tmp")),
            key=lambda p: p.stat().st_mtime,
        )
        if backup_dir.is_dir()
        else []
    )
    try:
        status = json.loads((backup_dir / "status.json").read_text())
    except (OSError, ValueError):
        status = {}

    latest = files[-1] if files else None
    last_backup_at = datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc) if latest else None
    last_error_at = _parse_iso(status.get("last_error_at"))
    # Un échec n'est affiché que s'il est postérieur à la dernière sauvegarde réussie
    failing = bool(status.get("last_error")) and (last_backup_at is None or (last_error_at or now) > last_backup_at)
    # « Configuré » = au moins une sauvegarde ou une tentative : sinon (dev local) rien à signaler
    configured = latest is not None or bool(status)
    return {
        "configured": configured,
        "last_backup_at": last_backup_at,
        "last_backup_file": latest.name if latest else None,
        "encrypted": latest.name.endswith(".enc") if latest else None,
        "backup_count": len(files),
        "last_auto_success_at": _parse_iso(status.get("last_auto_success_at")),
        "last_attempt_at": _parse_iso(status.get("last_attempt_at")),
        "last_error": status.get("last_error") if failing else None,
        "last_error_at": last_error_at if failing else None,
        "github_configured": github_configured,
        "github_last_sync_at": _parse_iso(status.get("github_last_sync_at")),
        "github_error": status.get("github_error") if github_configured else None,
        "stale": configured and (last_backup_at is None or now - last_backup_at > BACKUP_STALE_AFTER),
    }
