# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Présentation

Application web **self-hosted** de suivi budget et investissement (« Numera » / « Suivi Budget »), usage personnel mono-utilisateur. Remplace un tableur Numbers. Données locales (SQLite) ; seules appelées en externe : Frankfurter (taux de change), les données de marché (`core/market_data.py`) et, si l'utilisateur les active, ntfy / Telegram pour les notifications (`services/notifications.py (canaux : integrations/notifications.py)`).

Stack : React 18 + Vite + TypeScript + Tailwind + Recharts (frontend) · FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2 (backend) · SQLite (`backend/data/suivi_budget.db`) · Docker Compose.

## Carte de la documentation

| Besoin | Où |
|---|---|
| Conventions backend / frontend | `backend/CLAUDE.md`, `frontend/src/CLAUDE.md` (chargés automatiquement dans ces dossiers) |
| Procédures détaillées | skills `.claude/skills/` : `numera-expert` (métier), `numera-backend`, `numera-frontend`, `numera-testing` |
| Architecture, modèle de données, routes API | `ARCHITECTURE.md` |
| Exploitation backend (logs, déploiement, sécurité) | `docs/BACKEND.md`, `backend/LOGGING.md`, `docs/BACKUP_RESTORE.md` |
| Centre d'Actions (audit, alertes budget, suggestions de règles) | `docs/ACTION_CENTER.md` |
| Serveur MCP | `mcp-server/README.md` |
| Guide agent historique (fichier local, ignoré par git) | `AGENT.MD` |
| Suivi produit (historique, non maintenu à chaque changement) | `PLAN.MD`, `ROADMAP.md`, `TEST_PLAN.md` |

Quand le code change une route, un modèle, une commande ou une règle métier, mettre à jour `ARCHITECTURE.md` et, si besoin, le skill concerné dans le même commit.

## Commandes

> Python 3.14+ : pydantic-core incompatible. Utiliser Python 3.11 ou 3.12.

```bash
make setup                 # premier lancement (setup.sh), crée .env depuis .env.example
make dev                   # Docker : docker compose -f infra/docker-compose.yml up --build
make prod                  # docker-compose.prod.yml
make test                  # pytest backend (backend/venv si présent, sinon python3.12/3.11 ; PYTHON=... pour forcer)
make check-size            # plafonds de taille (fichier/fonction), baseline à cliquet scripts/code_size_baseline.json
make validate              # check-size + tests backend + build frontend
make backend-seed-demo     # données de démo (backend/data/demo.db, jamais la vraie base)
make demo / demo-down      # instance de démo publique (docker-compose.demo.yml, port 8090, demo/demo)
make backup-now            # backup dans le conteneur

# Dev local
cd backend && uvicorn app.main:app --reload --port 8001
cd frontend && npm run dev          # port 5173
cd frontend && npm run build        # tsc --noEmit + vite build : seule vérification frontend (pas de lint/test)
cd frontend && npm run typecheck    # tsc seul

# Un seul test
cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_tags.py -v   # PYTHONPATH=. requis
cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_tags.py::test_name -v
cd backend && PYTHONPATH=. python3.11 -m pytest tests -q     # suite complète : ~840 tests, ~1 min 40

# Mot de passe admin (hash à mettre dans ADMIN_PASSWORD_HASH ; doubler les $ dans docker-compose)
python scripts/change_password.py <mot-de-passe>
```

## Architecture

### Backend (`backend/app/`)
- `main.py` : lifespan (migrations Alembic + seed), middleware de logs, CORS via `settings.cors_origins` (pas `*`). Les routers sont dans la liste `protected_routers` et reçoivent tous `Depends(get_current_user)` (JWT) ; seuls `health` et `auth` sont publics. **Un nouveau router doit être ajouté à cette liste.**
- **Architecture en couches** (migration en cours, cf. `ARCHITECTURE.md` § Couches backend) : `controllers/` (controllers) → `services/` (cas d'usage, commit, erreurs métier `core/errors.py`) → `repositories/` (requêtes) / `domain/` (calculs purs) / `integrations/` (appels externes). Règles d'import vérifiées par `tests/test_architecture.py`, tailles par `scripts/check_code_size.py` (baselines à cliquet : ne jamais les augmenter). Modèle à suivre : `accounts`. Code déplacé : supprimé de l'ancien emplacement, sans ré-export.
- `controllers/` : un router par domaine (accounts, transactions, imports, holdings, market, etf_profiles, diversity, salary, merchants, …). `controllers/analytics/` est un **package** (metrics, budget, investments, insights, reports, subscriptions, audit, diversity) ; budget, Centre d'Actions et projection de trésorerie sont calculés dans `services/analytics/` et `services/audit.py`, les requêtes partagées dans `repositories/analytics/common.py`.
- `core/` : `config.py` (pydantic-settings, validation stricte des secrets en `APP_ENV=prod`), `security.py` + `login_rate_limit.py` (auth mono-utilisateur `ADMIN_USERNAME`/`ADMIN_PASSWORD_HASH` ; limiteurs `login_rate_limiter` / `totp_rate_limiter`), `errors.py` (erreurs métier), `finance.py` (soldes, `normalize_transaction_type`), `currency.py`, `recurring.py`, `salary.py`, `market_data.py`, `etf_analyzer.py`, `seeds*.py`, `migrations.py`.
- `models/` (SQLAlchemy 2 `Mapped`/`mapped_column`), `schemas/` (Pydantic, `from_attributes=True`), `db/session.py`. Schéma modifié → nouvelle migration Alembic dans `backend/alembic/versions/`.
- Tests (`backend/tests/`) : `conftest.py` fixe `APP_ENV=test`, mot de passe admin `admin`, DB SQLite temporaire par test et override de `get_db`/`get_current_user`. Vérifier l'effet en base, pas seulement le code HTTP.

### Frontend (`frontend/src/`)
- `lib/api.ts` : `apiFetch()` + `api.get/post/patch/delete` (JWT, `Content-Type: application/json` par défaut ; les uploads CSV de l'import utilisent `fetch()` direct, sans ce header, pour le multipart).
- `pages/` (une par route, react-router v7 dans `App.tsx`, protégé par `components/layout/ProtectedRoute`) ; composants par domaine dans `components/{analytics,dashboard,investments,settings,tools,layout}` ; primitives shadcn/Radix dans `components/ui`. `Dashboard` est découpé via `components/dashboard/tabs` et le hook `useDashboardData`.

### Serveur MCP (`mcp-server/`)
**Lecture seule.** Dispatcher `server.py` → `server_api.py` (proxy de l'API FastAPI authentifié par token MCP généré dans Paramètres → Sécurité, exposé sur `/mcp` par Nginx ; 47 outils ; mode recommandé, KPI calculés par le backend) ou `server_sqlite.py` (SQLite direct en `mode=ro`, stdio, 20 outils). L'API refuse toute méthode autre que `GET` avec un token MCP : ne pas ajouter d'outil d'écriture. Clients : Claude Code (`claude mcp add --transport http`) et Claude Desktop (pont `mcp-remote`). Détails : `mcp-server/README.md`. Toute nouvelle route de lecture exposable doit être répercutée dans `server_api.py`.

## Modèle de données

- `accounts.type` : `courant`, `epargne`, `investissement`, `assurance_vie` (validé à la création/modification ; un ancien type inconnu reste lisible).
- `transactions.type` : `Entree`, `Sortie`, `Interets`, `Solde Initial` (base du solde, exclue des KPI revenus/dépenses).
- `investment_transactions.type` : `versement`, `retrait`, `achat`, `vente`, `frais`, `dividende` (dividende non compté dans le montant investi). Valeur d'un compte titres = positions × cours + espèces (`core/portfolio.py`).
- Positions titres : `portfolio_holding` / `controllers/holdings.py` ; profils ETF : `etf_profile`.

## Règles métier critiques

1. Montants **toujours positifs** ; le sens est porté par `type`.
2. **KPI calculés côté backend uniquement** (`controllers/analytics/`), jamais côté frontend.
3. `running_balance` recalculé intégralement après toute création/modification/suppression (`recalculate_running_balances` dans `services/balances.py`).
4. Import CSV **idempotent** : doublon = `(account_id, date, amount, merchant, type)`. Le commit insère avec un solde courant partant de la dernière transaction, puis appelle `recalculate_running_balances` si au moins une ligne est importée (les soldes sont donc corrects même pour des données antérieures).
5. Un seul `is_zero_point = True` par compte investissement.
6. Salaire (`services/salary_generation.py`, montant `domain/salary.py::salary_amount`) : **une seule** transaction `Entree` « Salaire » = `net_salary − (nb jours TT × ticket_employee_share)`, rattachée à la récurrence salaire. Les tickets restaurant sont informatifs, aucune transaction TR n'est créée. Génération idempotente (`SalaryMonth.is_generated`).
7. Normalisation marchands : `merchant_id` relie à un marchand canonique sans modifier le libellé bancaire `merchant`.
8. Vérification de compte : `last_verified_at` mis à jour par validation explicite.
9. `normalize_transaction_type()` mappe `"type"` → `"Solde Initial"` volontairement (export Numbers).
10. Revue de fin de mois (`/month-review`) : clôturer = **marquer**, jamais verrouiller ; `transactions.is_exceptional` reste dans les totaux officiels et les soldes, seules les lectures « hors exceptionnel » (rapport mensuel, revue) l'isolent.

11. **Revenu** = entrées sur un compte `courant` (+ intérêts) ; une entrée sur un autre compte n'en est un que si sa catégorie est de type `revenu` (`income_criterion`, `repositories/analytics/common.py`). Même définition dans budget, money-flow, Sankey, kpi-history, timeseries. **Patrimoine** = tous les comptes actifs, tous types, via `core/wealth.py::account_values` (source unique).

Pipeline import : détection du délimiteur (`,` `;` `\t`) → en-têtes normalisés via `HEADER_ALIASES` → mapping catégories (manuel puis auto-création si `create_missing_categories=True`) → détection doublons → insert + log dans `imports_log`.

Multi-devises : Frankfurter, taux courants cachés 6 h en mémoire, historiques en base (`historical_exchange_rates`), fallback offline `EUR=1.0, USD=1.08, GBP=0.84, CHF=0.95`. Passer par `convert_amount` / `get_exchange_rates` (async). Stocker `amount` (devise du compte) + `original_amount` et `currency` (saisie d'origine).

## Outils MCP Distill (préférences du projet)

- Exploration de code : `mcp__distill__smart_file_read` (avec `target` pour une fonction/classe). Utiliser `Read` natif avant un `Edit` et pour les fichiers de config/`.md`/`.env`.
- Sortie Bash volumineuse (>500 car.) : `mcp__distill__auto_optimize`.
- Opérations multi-étapes : `mcp__distill__code_execute` (SDK `ctx.files/code/git/search/analyze/compress`).
- Ne pas envoyer de fichiers entiers sans nécessité ; préférer symboles, fonctions et diffs.
