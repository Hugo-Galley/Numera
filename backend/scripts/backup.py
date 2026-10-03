import os
import sqlite3
import datetime
import logging
import sys
from cryptography.fernet import Fernet
from pathlib import Path

# Configuration
DB_PATH = os.getenv("DB_PATH", "/app/data/suivi_budget.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/app/backups")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "7"))
BACKUP_KEY = os.getenv("BACKUP_KEY")
APP_ENV = os.getenv("APP_ENV", "dev")

INSECURE_BACKUP_KEYS = {"", "generate-a-fernet-key-using-python"}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def _snapshot_database(dest: str) -> None:
    """Copie cohérente de la base via l'API de backup SQLite.

    Une simple copie du fichier .db est incorrecte en mode WAL : les écritures récentes
    sont encore dans le fichier -wal et la copie peut être incohérente.
    """
    source = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=30)
    try:
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()

    check = sqlite3.connect(dest)
    try:
        result = check.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        check.close()
    if result != "ok":
        raise RuntimeError(f"Backup integrity check failed: {result}")


def create_backup() -> bool:
    """Crée un backup. Retourne True en cas de succès, lève une exception sinon."""
    if APP_ENV == "prod" and BACKUP_KEY in INSECURE_BACKUP_KEYS:
        raise RuntimeError("BACKUP_KEY must be configured in production")
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    # Valide la clé avant toute écriture : une clé invalide ne doit pas produire de fichier inutilisable
    fernet = None
    if BACKUP_KEY and BACKUP_KEY not in INSECURE_BACKUP_KEYS:
        fernet = Fernet(BACKUP_KEY.encode())

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(BACKUP_DIR) / f"suivi_budget_{timestamp}.db"
    temp_path = f"{backup_path}.tmp"

    try:
        _snapshot_database(temp_path)
        logging.info(f"Created consistent snapshot: {temp_path}")

        if fernet:
            with open(temp_path, "rb") as f:
                encrypted_data = fernet.encrypt(f.read())
            final_path = f"{backup_path}.enc"
            with open(final_path, "wb") as f:
                f.write(encrypted_data)
            logging.info(f"Backup encrypted and saved to {final_path}")
        else:
            final_path = str(backup_path)
            os.replace(temp_path, final_path)
            temp_path = None
            logging.warning(f"Backup saved UNENCRYPTED to {final_path} (no BACKUP_KEY)")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
    return True


def cleanup_old_backups() -> None:
    """Supprime les backups plus vieux que RETENTION_DAYS, en gardant toujours le plus récent."""
    logging.info(f"Cleaning up backups older than {RETENTION_DAYS} days...")
    cutoff = datetime.datetime.now() - datetime.timedelta(days=RETENTION_DAYS)

    backups = sorted(
        (p for p in Path(BACKUP_DIR).iterdir() if p.is_file() and p.name.startswith("suivi_budget_")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for file_path in backups[1:]:  # le plus récent est toujours conservé
        if datetime.datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff:
            logging.info(f"Deleting old backup: {file_path.name}")
            file_path.unlink()


if __name__ == "__main__":
    logging.info("Starting backup process...")
    try:
        create_backup()
    except Exception as exc:
        # Échec visible (code de sortie != 0) et AUCUN nettoyage : on ne supprime pas
        # les anciens backups tant qu'on n'est pas sûr d'en avoir un récent valide.
        logging.error(f"Backup failed: {exc}")
        sys.exit(1)
    cleanup_old_backups()
    logging.info("Backup process completed.")
