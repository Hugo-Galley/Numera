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

## Envoi automatique vers GitHub

Le bouton « Sauvegarder maintenant » (Paramètres → Données) lance la même chaîne à la demande (`POST /admin/backup/run`, `BACKUP_TRIGGER=manual`) et affiche une popin à la fin.

Chaque exécution de `backup.py` met à jour `BACKUP_DIR/status.json` (dernière tentative, dernière réussite, dernière réussite automatique, dernière erreur, dernier envoi GitHub ou son erreur). L'API le lit avec les fichiers `suivi_budget_*` (`GET /admin/backup/status`) : la carte Sauvegarde l'affiche et le Centre d'actions lève « Sauvegarde en retard » (aucune sauvegarde depuis 2 jours) ou « Dernière sauvegarde en échec ». Sans aucune sauvegarde ni `status.json` (dev local), rien n'est signalé.

Après chaque sauvegarde (toutes les 24 h via le conteneur `backup`), `backend/scripts/git_sync.py` pousse les fichiers `.enc` vers un dépôt GitHub **privé et dédié** (jamais le dépôt du code, qui est public). Seules les sauvegardes chiffrées sont envoyées : sans `BACKUP_KEY`, rien ne part.

1. Créer un dépôt privé vide (ex. `numera-backups`).
2. Créer un token fine-grained limité à ce dépôt, permission *Contents : Read and write*.
3. Renseigner dans `.env` : `GITHUB_BACKUP_REPO=Hugo-Galley/numera-backups` et `GITHUB_BACKUP_TOKEN=...`, puis `docker compose up -d --build backup`.

Le dépôt garde **une sauvegarde par jour** (la dernière du jour), rangée par mois (`2026-10/…`), sur `GITHUB_BACKUP_KEEP_DAYS` jours (30 par défaut) ; l'historique git conserve les anciennes versions. Un échec d'envoi sort en code 2 sans annuler la sauvegarde locale. **Conservez `BACKUP_KEY` ailleurs** (gestionnaire de mots de passe) : sans elle, les sauvegardes GitHub sont illisibles.

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


## Garanties de `restore.py`

- La sauvegarde est déchiffrée et vérifiée (`PRAGMA integrity_check`) dans un fichier temporaire **avant** toute écriture : une mauvaise clé ou un fichier corrompu laisse la base actuelle intacte.
- La base remplacée est conservée à côté (`<destination>.pre-restore-<horodatage>`), puis le remplacement est atomique.
- Le script sort avec un code non nul en cas d'échec.
- Arrêtez le backend avant de restaurer (`docker compose stop backend`). Les logos (`backend/data/logos`) ne sont pas inclus dans les sauvegardes.
