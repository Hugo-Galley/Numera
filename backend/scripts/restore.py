import os
import logging
import argparse
from cryptography.fernet import Fernet
from pathlib import Path
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def restore_backup(backup_file, dest_db, key):
    if not os.path.exists(backup_file):
        logging.error(f"Backup file not found: {backup_file}")
        return

    try:
        if backup_file.endswith(".enc"):
            if not key:
                logging.error("Backup is encrypted but no key was provided.")
                return
            
            logging.info(f"Decrypting {backup_file}...")
            fernet = Fernet(key.encode())
            with open(backup_file, "rb") as f:
                encrypted_data = f.read()
            
            decrypted_data = fernet.decrypt(encrypted_data)
            
            with open(dest_db, "wb") as f:
                f.write(decrypted_data)
            logging.info(f"Backup decrypted and restored to {dest_db}")
        else:
            logging.info(f"Restoring {backup_file} to {dest_db}...")
            shutil.copy2(backup_file, dest_db)
            logging.info("Backup restored.")

    except Exception as e:
        logging.error(f"Restore failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore a backup of the suivi-budget database.")
    parser.add_argument("backup_file", help="Path to the backup file (.db or .db.enc)")
    parser.add_argument("--dest", default="backend/data/suivi_budget.db", help="Destination path for the restored database")
    parser.add_argument("--key", help="Decryption key (if encrypted)")

    args = parser.parse_args()
    
    # If key not provided via arg, try env
    key = args.key or os.getenv("BACKUP_KEY")
    
    restore_backup(args.backup_file, args.dest, key)
