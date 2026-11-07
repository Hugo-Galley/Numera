# Backup and restore procedure

This document describes how to back up and restore the application's SQLite database.

## Backup

The system uses a Python script, `backend/scripts/backup.py`, which can be run manually or through Docker.

### Environment variables
- `DB_PATH`: path to the database (default: `/app/data/suivi_budget.db`)
- `BACKUP_DIR`: folder where backups are stored (default: `/app/backups`)
- `BACKUP_KEY`: (optional) Fernet key used to encrypt the backup.
- `RETENTION_DAYS`: number of days backups are kept (default: 7).
- `BACKUP_INTERVAL_SECONDS`: delay between two automatic backups of the `backup` container (default: 86400).
- `GITHUB_BACKUP_KEEP_DAYS`: days kept on GitHub (default: 30).

These settings go in `.env`; the compose files pass them on to the `backend` and `backup` containers.

### Backup before migration

At startup, `run_migrations()` (`backend/app/core/migrations.py`) compares the database's Alembic revision with the head of the migrations. If the schema has to change (version update), the database is copied into `BACKUP_DIR` as `pre_migration_<revision>_<date>.db` (`.db.enc`, encrypted with `BACKUP_KEY`, if it is set) before any `alembic upgrade`. The 5 most recent are kept; they are neither sent to GitHub nor touched by the `RETENTION_DAYS` rotation. If the copy fails, the application refuses to start rather than migrate without a safety net. Brand-new or already up-to-date database: no copy. Restore: see below, as for a normal backup.

### Docker update

`install.sh --upgrade` backs up (`backup` container), downloads the release's compose file again, verifies `SHA256SUMS`, pulls the images and restarts. See the README, "Updating" section.

### Manual run
```bash
PYTHONPATH=backend python3 backend/scripts/backup.py
```

## Automatic upload to GitHub

The "Sauvegarder maintenant" ("Back up now") button (Paramètres → Données / Settings → Data) triggers the same chain on demand (`POST /admin/backup/run`, `BACKUP_TRIGGER=manual`) and shows a dialog when it finishes.

Each run of `backup.py` updates `BACKUP_DIR/status.json` (last attempt, last success, last automatic success, last error, last GitHub upload or its error). The API reads it together with the `suivi_budget_*` files (`GET /admin/backup/status`): the Backup card displays it and the Action Center raises "Sauvegarde en retard" ("Backup overdue", no backup for 2 days) or "Dernière sauvegarde en échec" ("Last backup failed"). With no backup and no `status.json` at all (local dev), nothing is reported.

After each backup (every 24 h through the `backup` container), `backend/scripts/git_sync.py` (the token is passed to `git` through the `GIT_CONFIG_*` environment, never in `argv`) pushes the `.enc` files to a **private, dedicated** GitHub repository (never the code repository, which is public). Only encrypted backups are sent: without `BACKUP_KEY`, nothing leaves the machine.

1. Create an empty private repository (e.g. `numera-backups`).
2. Create a fine-grained token limited to that repository, with the *Contents: Read and write* permission.
3. Set in `.env`: `GITHUB_BACKUP_REPO=Hugo-Galley/numera-backups` and `GITHUB_BACKUP_TOKEN=...`, then `docker compose up -d --build backup`.

The repository keeps **one backup per day** (the last of the day), organised by month (`2026-10/…`), for `GITHUB_BACKUP_KEEP_DAYS` days (30 by default); git history keeps older versions. An upload failure exits with code 2 without cancelling the local backup. **Keep `BACKUP_KEY` somewhere else** (password manager): without it, the GitHub backups are unreadable.

## Restore

To restore a backup, use the `backend/scripts/restore.py` script.

### Syntax
```bash
PYTHONPATH=backend python3 backend/scripts/restore.py <backup_file> --dest <destination> --key <key_if_encrypted>
```

### Restore example (unencrypted)
```bash
PYTHONPATH=backend python3 backend/scripts/restore.py backups/suivi_budget_20260605_120000.db --dest backend/data/suivi_budget.db
```

### Restore example (encrypted)
```bash
export BACKUP_KEY=your_secret_key
PYTHONPATH=backend python3 backend/scripts/restore.py backups/suivi_budget_20260605_120000.db.enc --dest backend/data/suivi_budget.db
```

## Procedure validation

The procedure was validated on 5 June 2026:
1. Creation of a dummy database.
2. Run of `backup.py`.
3. Deletion of the dummy database.
4. Run of `restore.py`.
5. Integrity check of the restored data.


## Guarantees of `restore.py`

- The backup is decrypted and checked (`PRAGMA integrity_check`) in a temporary file **before** anything is written: a wrong key or a corrupted file leaves the current database untouched.
- The replaced database is kept alongside (`<destination>.pre-restore-<timestamp>`), then the replacement is atomic.
- The script exits with a non-zero code on failure.
- Stop the backend before restoring (`docker compose stop backend`). Logos (`backend/data/logos`) are not included in backups.

## Automatic verification

`backend/tests/systeme/test_backup_roundtrip.py` (part of the pytest suite, hence CI) does a real round trip: a database migrated by Alembic in WAL mode with a write still in the `-wal` file, `backup.py` (plain and encrypted), `restore.py`, then a table-by-table comparison, a schema identical to the models, and `PRAGMA integrity_check`. A backup that can no longer be restored fails the CI.
