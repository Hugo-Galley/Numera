import argparse
import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def _remove_stale_wal_files(dest_db):
    """Un -wal/-shm résiduel serait rejoué sur la base restaurée et la corromprait."""
    for suffix in ("-wal", "-shm"):
        stale = f"{dest_db}{suffix}"
        if os.path.exists(stale):
            os.remove(stale)
            logging.info(f"Removed stale {stale}")


def _integrity_ok(path):
    """Le fichier est une base SQLite lisible et cohérente."""
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            return con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            con.close()
    except sqlite3.DatabaseError:
        return False


def restore_backup(backup_file, dest_db, key):
    """Restaure `backup_file` dans `dest_db`. Retourne True en cas de succès, False sinon.

    La base de destination n'est jamais touchée avant que la sauvegarde ait été déchiffrée et vérifiée
    (`PRAGMA integrity_check`) dans un fichier temporaire ; l'ancienne base est conservée à côté
    (`<dest>.pre-restore-<horodatage>`) puis le remplacement est atomique.
    """
    if not os.path.exists(backup_file):
        logging.error(f"Backup file not found: {backup_file}")
        return False

    dest_dir = os.path.dirname(os.path.abspath(dest_db))
    os.makedirs(dest_dir, exist_ok=True)
    temp_path = f"{dest_db}.restore.tmp"

    try:
        if backup_file.endswith(".enc"):
            if not key:
                logging.error("Backup is encrypted but no key was provided.")
                return False
            logging.info(f"Decrypting {backup_file}...")
            with open(backup_file, "rb") as f:
                data = Fernet(key.encode()).decrypt(f.read())
            with open(temp_path, "wb") as f:
                f.write(data)
        else:
            shutil.copy2(backup_file, temp_path)

        if not _integrity_ok(temp_path):
            logging.error("The backup is not a valid SQLite database (integrity check failed): destination left untouched.")
            return False

        if os.path.exists(dest_db):
            saved = f"{dest_db}.pre-restore-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(dest_db, saved)
            logging.info(f"Previous database kept as {saved}")
        _remove_stale_wal_files(dest_db)
        os.replace(temp_path, dest_db)
        temp_path = None
        logging.info(f"Backup restored to {dest_db}")
        return True

    except InvalidToken:
        logging.error("Decryption failed: wrong BACKUP_KEY or corrupted backup.")
        return False
    except Exception as e:
        logging.error(f"Restore failed: {e}")
        return False
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore a backup of the suivi-budget database.")
    parser.add_argument("backup_file", help="Path to the backup file (.db or .db.enc)")
    parser.add_argument("--dest", default="backend/data/suivi_budget.db", help="Destination path for the restored database")
    parser.add_argument("--key", help="Decryption key (if encrypted)")

    args = parser.parse_args()

    # If key not provided via arg, try env
    key = args.key or os.getenv("BACKUP_KEY")

    sys.exit(0 if restore_backup(args.backup_file, args.dest, key) else 1)
