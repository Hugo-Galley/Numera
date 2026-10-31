#!/bin/sh
# Backend dédié aux tests E2E : base de démo jetable (régénérée à chaque lancement), jamais la vraie.
# Identifiants demo / demo, comme sur l'instance de démonstration.
set -eu
cd "$(dirname "$0")/../../backend"

PY="${E2E_PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x venv/bin/python ]; then PY=venv/bin/python
  elif command -v python3.12 >/dev/null 2>&1; then PY=python3.12
  else PY=python3.11
  fi
fi

mkdir -p data
rm -f data/e2e-demo.db data/e2e-demo.db-shm data/e2e-demo.db-wal

export PYTHONPATH=.
export APP_ENV=dev
export DEMO_MODE=true
export DATABASE_URL=sqlite:///./data/e2e-demo.db
export SECRET_KEY=e2e-secret-key-not-used-outside-tests-0123456789abcdef
export ADMIN_USERNAME=demo
export ADMIN_PASSWORD_HASH='$2b$12$Slulk5dFY3RpgWFs21zh/OM9HTmvhxXQwruKFT5dAxZv7WxH6mUmm'
export CORS_ORIGINS=http://localhost:5174

"$PY" scripts/seed_demo.py
exec "$PY" -m uvicorn app.main:app --port 8101
