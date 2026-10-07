---
name: numera-testing
description: Comment lancer, écrire et déboguer les tests de Numera (pytest backend, build frontend) et ce qu'il faut vérifier avant de considérer une tâche terminée. À charger avant toute validation ou pour corriger un test en échec.
---

# Numera — tests et validation

## Lancer les tests backend

Depuis `backend/` (le `PYTHONPATH` est obligatoire, sinon `ModuleNotFoundError: app`) :

```bash
PYTHONPATH=. python3.11 -m pytest tests -q                       # tout : 168 tests, ~13 s
PYTHONPATH=. python3.11 -m pytest tests/test_merchants.py -v     # un fichier
PYTHONPATH=. python3.11 -m pytest tests/test_tags.py::test_x -v  # un test
```

- `make test` / `make validate` choisissent l'interpréteur automatiquement : `backend/venv/bin/python` si présent, sinon `python3.12`, sinon `python3.11` (surchargeable : `make test PYTHON=...`). `backend/venv_new` est en Python 3.14 sans pytest, et pydantic-core ne supporte pas 3.14.
- Dépendances : `backend/requirements.txt` (jose, bcrypt, httpx, etc.).

## Infrastructure de test (`tests/conftest.py`)

- `APP_ENV=test` : pas de migrations ni de seed au démarrage ; tables créées par `Base.metadata.create_all` sur une SQLite temporaire (`tmp_path`) propre à chaque test.
- `ADMIN_PASSWORD_HASH` fixé sur le mot de passe `admin`.
- Fixtures : `db_session` (Session) et `client` (TestClient avec `get_db` — deux chemins d'import — et `get_current_user` surchargés ; le rate limiter de login est réinitialisé).
- Un `401` en test signifie presque toujours que `client` n'est pas utilisé ou que l'override n'est pas actif.
- `database is locked` : un autre process garde la base ouverte.

## Écrire un test

Fichier `tests/test_<domaine>.py`. Créer les données via `db_session` ou l'API (`client.post`), appeler l'endpoint, vérifier le code HTTP **et** l'état en base (soldes, flags, liens). Un test par bug corrigé.

## Points de vérification selon le changement

- Transactions : `running_balance` cohérent après create/update/delete/bulk/import (`test_import_and_analytics.py`, `test_transfers.py`).
- Devises : `original_amount` + `currency` conservés, `amount` converti dans la devise du compte.
- Marchands / règles / tags : `test_merchants.py`, `test_categorization_rules.py`, `test_tags.py`.
- Salaire : transaction unique « Salaire », `is_generated` posé, pas de doublon (`test_p0_features.py` à consulter).
- Centre d'Actions / audit : l'issue résolue disparaît de `/analytics/actions` (`test_data_audit.py`, `test_anomaly_detection.py`).
- Analytics : `test_money_flow.py`, `test_sankey.py`, `test_cashflow_projection.py`, `test_asset_allocation.py`, `test_diversity_scanner.py`, `test_simulation.py`, `test_subscriptions.py`, `test_savings_goals.py`, `test_calendar.py`, `test_excluded_months.py`, `test_filtering.py`.
- Auth / config : `test_auth.py`, `test_config.py`.

## Frontend

Aucun test automatisé. `cd frontend && npm run build` (= `tsc --noEmit && vite build` ; 0 erreur de types actuellement, ne pas en introduire). Contrôles manuels : mode confidentialité, toasts, thème sombre, mobile.

## Définition de « terminé »

Tests backend verts, build frontend OK, nouveau test pour le comportement ajouté, docs concernées mises à jour (`ARCHITECTURE.md`, skills, CLAUDE.md).
