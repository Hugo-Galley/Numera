import time
import subprocess
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INTERVAL = int(os.getenv("BACKUP_INTERVAL_SECONDS", "86400")) # Default 24h

def run_backup():
    logging.info("Triggering backup script...")
    try:
        subprocess.run(["python", "/app/scripts/backup.py"], check=True)
        logging.info("Backup script finished successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Backup script failed with exit code {e.returncode}")

if __name__ == "__main__":
    logging.info(f"Backup scheduler started. Interval: {INTERVAL} seconds.")
    # Run once at startup
    run_backup()
    
    while True:
        time.sleep(INTERVAL)
        run_backup()
