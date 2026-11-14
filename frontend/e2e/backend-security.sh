#!/bin/sh
# Backend des E2E « sécurité / système » : base jetable NON démo (régénérée à chaque lancement, jamais la vraie),
# car le mode démo bloque 2FA, passkeys, jetons MCP, sauvegardes et notifications.
# Identifiants de test posés ici : e2e / e2e-security-pass (aucun secret réel). Sorties réseau neutralisées :
# tout HTTPS sortant passe par le faux serveur (mock-external.mjs, port 8103) qui le refuse et le journalise.
set -eu
cd "$(dirname "$0")/../../backend"

PY="${E2E_PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x .venv/bin/python ]; then PY=.venv/bin/python
  elif [ -x venv/bin/python ]; then PY=venv/bin/python
  elif command -v python3.12 >/dev/null 2>&1; then PY=python3.12
  else PY=python3.11
  fi
fi

DATA="$PWD/data"
rm -rf "$DATA/e2e-security.db" "$DATA/e2e-security.db-shm" "$DATA/e2e-security.db-wal" "$DATA/e2e-security-backups"
mkdir -p "$DATA"

export PYTHONPATH=.
export APP_ENV=dev
export DATABASE_URL="sqlite:///$DATA/e2e-security.db"
export SECRET_KEY=e2e-security-secret-key-not-used-outside-tests-0123456789
export ADMIN_USERNAME=e2e
export ADMIN_PASSWORD_HASH='$2b$12$.yt2IYLMSR7JQRgcHRdC2uSds1zMB9hSXWahSQrXW1RJziDo0Qr.6'
export CORS_ORIGINS=http://localhost:5175
export LOGIN_MAX_ATTEMPTS=100
# Sauvegardes : script lancé par l'API (DB_PATH / BACKUP_DIR / BACKUP_KEY), clé Fernet de test
export DB_PATH="$DATA/e2e-security.db"
export BACKUP_DIR="$DATA/e2e-security-backups"
# Clé Fernet de test dérivée d'une phrase de 32 octets exactement (support.ts calcule la même), aucun secret réel
BACKUP_KEY="$("$PY" -c 'import base64;print(base64.urlsafe_b64encode(b"e2e-security-backup-key-32bytes!").decode())')"
export BACKUP_KEY
export GITHUB_BACKUP_REPO= GITHUB_BACKUP_TOKEN=
# Aucun appel réel : HTTPS_PROXY mène au faux serveur (Telegram, Frankfurter, Yahoo y échouent), ntfy local en direct
export HTTPS_PROXY=http://127.0.0.1:8103
export HTTP_PROXY=
export NO_PROXY=127.0.0.1,localhost

exec "$PY" -m uvicorn app.main:app --port 8102
