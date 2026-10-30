---
name: numera-testing
description: Comment lancer, écrire et déboguer les tests de Numera (pytest backend, Vitest frontend) et ce qu'il faut vérifier avant de considérer une tâche terminée. À charger avant toute validation ou pour corriger un test en échec.
---

# Numera — tests et validation

## Lancer les tests backend

Depuis `backend/` (le `PYTHONPATH` est obligatoire, sinon `ModuleNotFoundError: app`) :

```bash
PYTHONPATH=. python3.11 -m pytest tests -q                       # tout : ~910 tests, ~1 min 45
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

Le test s'écrit **avant** le code et doit être vu rouge (skill `numera-tdd`, qui dit aussi quel niveau choisir : `domain`, service, route). Fichier `tests/test_<domaine>.py`. Créer les données via `db_session` ou l'API (`client.post`), appeler l'endpoint, vérifier le code HTTP **et** l'état en base (soldes, flags, liens). Un test par bug corrigé.

## Points de vérification selon le changement

- Transactions : `running_balance` cohérent après create/update/delete/bulk/import (`test_import_and_analytics.py`, `test_transfers.py`).
- Devises : `original_amount` + `currency` conservés, `amount` converti dans la devise du compte.
- Marchands / règles / tags : `test_merchants.py`, `test_categorization_rules.py`, `test_tags.py`.
- Salaire : transaction unique « Salaire », `is_generated` posé, pas de doublon (`test_p0_features.py` à consulter).
- Centre d'Actions / audit : l'issue résolue disparaît de `/analytics/actions` (`test_data_audit.py`, `test_anomaly_detection.py`).
- Analytics, filet de non-régression : `tests/test_analytics_snapshots.py` compare la sortie JSON de toutes les routes analytics (budget, Centre d'Actions, métriques, rapports, insights, abonnements, bilan annuel, investissements, projections, fiscalité, revue de mois) aux instantanés de `tests/snapshots/analytics/`, sur les données de démo à date figée (`freezegun`, 2026-06-15 10:00) complétées pour déclencher chaque règle du Centre d'Actions. Un écart est un bug : **ne jamais régénérer les instantanés pour faire passer le test**. Régénération volontaire seulement pour un changement de chiffre voulu et justifié dans le commit : `UPDATE_SNAPSHOTS=1 PYTHONPATH=. python3.11 -m pytest tests/test_analytics_snapshots.py`.
- Portefeuille, même principe : `tests/test_portfolio_snapshots.py` (réutilise la fixture ci-dessus et ajoute un compte titres « CTO Instantané » avec Point Zéro, achat, vente en USD, frais, dividende avec retenue et relevés du courtier) fige `/analytics/portfolio[/{id}]`, `/analytics/dividends`, `/holdings`, `/holdings/estimate-costs`, `/investment-transactions`, `/analytics/diversity-scanner`, `/etf-profiles` et le rapprochement courtier (`/analytics/actions`) dans `tests/snapshots/portfolio/`. Les appels Yahoo sont neutralisés par patch de `integrations/yahoo_finance.py` (`fetch_chart`, `fetch_composition`), jamais en désactivant `block_network`.
- Analytics : `test_money_flow.py`, `test_sankey.py`, `test_cashflow_projection.py`, `test_asset_allocation.py`, `test_diversity_scanner.py`, `test_simulation.py`, `test_subscriptions.py`, `test_savings_goals.py`, `test_calendar.py`, `test_excluded_months.py`, `test_filtering.py`.
- Auth / config : `test_auth.py`, `test_config.py`.

## Frontend

```bash
cd frontend && npm test                                   # tout (vitest run) ; make test-front depuis la racine
cd frontend && npx vitest run src/lib/utils.test.ts       # un fichier
cd frontend && npx vitest run -t "formatCurrency"         # par nom de test
cd frontend && npm run test:watch                         # en continu
cd frontend && npm run build                              # tsc app + tests (0 erreur), puis vite build
```

Les deux sont obligatoires : `npm test` ne vérifie pas les types, le build ne lance pas les tests. Conventions (emplacement `X.test.tsx`, `renderWithProviders`, handlers MSW par domaine, fabriques, horloge figée) : `frontend/src/CLAUDE.md` § Vérification.

Débogage : « Requête(s) sans handler MSW : GET … » = ajouter un handler (`server.use(...)` dans le test, ou `src/test/handlers/<domaine>.ts`) ; `localStorage` indéfini sous Node ≥ 25 = lancer via `npm test` / `vitest.config.ts` (option `--no-experimental-webstorage`) ; un élément introuvable : `screen.debug()`, et `findBy…` pour ce qui s'affiche après une requête. Contrôles manuels en plus : mode confidentialité, toasts, thème sombre, mobile.

## Définition de « terminé »

Checklist complète (validation selon le changement, docs, commit) : skill `numera-finishing`.
