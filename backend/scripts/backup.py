import os
import shutil
import datetime
import logging
from cryptography.fernet import Fernet
from pathlib import Path

# Configuration
DB_PATH = os.getenv("DB_PATH", "/app/data/suivi_budget.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/app/backups")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "7"))
BACKUP_KEY = os.getenv("BACKUP_KEY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_backup():
    if not os.path.exists(DB_PATH):
        logging.error(f"Database not found at {DB_PATH}")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"suivi_budget_{timestamp}.db"
    backup_path = Path(BACKUP_DIR) / backup_filename

    try:
        # 1. Create a temporary copy
        temp_path = f"{backup_path}.tmp"
        shutil.copy2(DB_PATH, temp_path)
        logging.info(f"Created temporary backup: {temp_path}")

        # 2. Encrypt if key is provided
        if BACKUP_KEY:
            logging.info("Encrypting backup...")
            fernet = Fernet(BACKUP_KEY.encode())
            with open(temp_path, "rb") as f:
                data = f.read()
            
            encrypted_data = fernet.encrypt(data)
            
            final_path = f"{backup_path}.enc"
            with open(final_path, "wb") as f:
                f.write(encrypted_data)
            
            os.remove(temp_path)
            logging.info(f"Backup encrypted and saved to {final_path}")
        else:
            os.rename(temp_path, backup_path)
            logging.info(f"Backup saved to {backup_path}")

    except Exception as e:
        logging.error(f"Backup failed: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)

def cleanup_old_backups():
    logging.info(f"Cleaning up backups older than {RETENTION_DAYS} days...")
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=RETENTION_DAYS)
    
    for filename in os.listdir(BACKUP_DIR):
        file_path = Path(BACKUP_DIR) / filename
        if file_path.is_file():
            file_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_time < cutoff:
                logging.info(f"Deleting old backup: {filename}")
                os.remove(file_path)

if __name__ == "__main__":
    logging.info("Starting backup process...")
    create_backup()
    cleanup_old_backups()
    logging.info("Backup process completed.")
