# Procédure de Sauvegarde et Restauration

Ce document décrit comment sauvegarder et restaurer la base de données SQLite de l'application.

## Sauvegarde

Le système utilise un script Python `backend/scripts/backup.py` qui peut être exécuté manuellement ou via Docker.

### Variables d'environnement
- `DB_PATH` : Chemin vers la base de données (défaut: `/app/data/suivi_budget.db`)
- `BACKUP_DIR` : Dossier où stocker les sauvegardes (défaut: `/app/backups`)
- `BACKUP_KEY` : (Optionnel) Clé Fernet pour chiffrer la sauvegarde.
- `RETENTION_DAYS` : Nombre de jours de rétention des sauvegardes (défaut: 7).

### Exécution manuelle
```bash
PYTHONPATH=backend python3 backend/scripts/backup.py
```

## Restauration

Pour restaurer une sauvegarde, utilisez le script `backend/scripts/restore.py`.

### Syntaxe
```bash
PYTHONPATH=backend python3 backend/scripts/restore.py <fichier_sauvegarde> --dest <destination> --key <cle_si_chiffre>
```

### Exemple de restauration (non chiffrée)
```bash
PYTHONPATH=backend python3 backend/scripts/restore.py backups/suivi_budget_20260605_120000.db --dest backend/data/suivi_budget.db
```

### Exemple de restauration (chiffrée)
```bash
export BACKUP_KEY=votre_cle_secrete
PYTHONPATH=backend python3 backend/scripts/restore.py backups/suivi_budget_20260605_120000.db.enc --dest backend/data/suivi_budget.db
```

## Validation de la procédure

La procédure a été validée le 5 juin 2026 :
1. Création d'une base factice.
2. Exécution de `backup.py`.
3. Suppression de la base factice.
4. Exécution de `restore.py`.
5. Vérification de l'intégrité des données restaurées.
