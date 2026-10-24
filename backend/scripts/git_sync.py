"""Envoie les sauvegardes chiffrées vers un dépôt GitHub privé dédié.

Variables d'environnement :
- `GITHUB_BACKUP_REPO` : `owner/nom` du dépôt (ex. `Hugo-Galley/numera-backups`). Vide = synchro désactivée.
- `GITHUB_BACKUP_TOKEN` : token GitHub (fine-grained, droit « Contents: read/write » sur ce seul dépôt).
- `BACKUP_KEY` : obligatoire, seuls les fichiers `.enc` sont envoyés (jamais de base en clair sur GitHub).
"""
import base64
import logging
import os
import shutil
import subprocess
from pathlib import Path

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/app/backups"))
REPO = os.getenv("GITHUB_BACKUP_REPO", "").strip()
TOKEN = os.getenv("GITHUB_BACKUP_TOKEN", "").strip()
WORK_DIR = BACKUP_DIR / ".git-sync"
BRANCH = "main"


def _git(*args: str, cwd: Path | None = None) -> str:
    # Le token passe par un en-tête http (jamais dans l'URL ni dans les logs).
    auth = base64.b64encode(f"x-access-token:{TOKEN}".encode()).decode()
    cmd = ["git", "-c", f"http.extraheader=Authorization: Basic {auth}", *args]
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        # stderr peut citer l'URL mais pas l'en-tête ; on masque le token par prudence.
        raise RuntimeError(f"git {args[0]} : {result.stderr.replace(TOKEN, '***').strip()}")
    return result.stdout


def _prepare_clone() -> None:
    url = os.getenv("GITHUB_BACKUP_URL") or f"https://github.com/{REPO}.git"  # surchargeable pour les tests
    if (WORK_DIR / ".git").exists():
        _git("fetch", "origin", cwd=WORK_DIR)
        try:
            _git("reset", "--hard", f"origin/{BRANCH}", cwd=WORK_DIR)
        except RuntimeError:  # dépôt encore vide
            pass
        return
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    WORK_DIR.mkdir(parents=True)
    _git("init", "-b", BRANCH, cwd=WORK_DIR)
    _git("remote", "add", "origin", url, cwd=WORK_DIR)
    _git("config", "user.name", "Numera backup", cwd=WORK_DIR)
    _git("config", "user.email", "backup@numera.local", cwd=WORK_DIR)
    try:
        _git("fetch", "origin", cwd=WORK_DIR)
        _git("reset", "--hard", f"origin/{BRANCH}", cwd=WORK_DIR)
    except RuntimeError:  # dépôt vide : premier push
        pass


def sync_backups() -> bool:
    """Reflète les sauvegardes chiffrées locales dans le dépôt GitHub. False si désactivé."""
    if not REPO:
        return False
    if not TOKEN:
        raise RuntimeError("GITHUB_BACKUP_TOKEN manquant")
    encrypted = sorted(BACKUP_DIR.glob("suivi_budget_*.db.enc"))
    if not encrypted:
        raise RuntimeError("Aucune sauvegarde chiffrée à envoyer (BACKUP_KEY configurée ?)")

    _prepare_clone()
    for old in WORK_DIR.glob("suivi_budget_*.db.enc"):
        old.unlink()  # même rétention que le dossier local
    for path in encrypted:
        shutil.copy2(path, WORK_DIR / path.name)

    _git("add", "-A", cwd=WORK_DIR)
    if not _git("status", "--porcelain", cwd=WORK_DIR).strip():
        logging.info("Dépôt GitHub déjà à jour.")
        return True
    _git("commit", "-m", f"Sauvegarde {encrypted[-1].name}", cwd=WORK_DIR)
    _git("push", "origin", f"HEAD:{BRANCH}", cwd=WORK_DIR)
    logging.info(f"Sauvegardes envoyées vers github.com/{REPO}")
    return True
