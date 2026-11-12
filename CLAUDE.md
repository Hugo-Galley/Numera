# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Présentation

Application web **self-hosted** de suivi budget et investissement (« Numera » / « Suivi Budget »), usage personnel mono-utilisateur. Remplace un tableur Numbers. Données locales (SQLite) ; seules appelées en externe : Frankfurter (taux de change), les données de marché (Yahoo Finance : `integrations/yahoo_finance.py`, via `services/investissement/market/`) et, si l'utilisateur les active, ntfy / Telegram pour les notifications (`services/systeme/notifications.py (canaux : integrations/notifications.py)`).

Stack : React 19 + Vite 8 (Rolldown) + TypeScript + Tailwind + Recharts (frontend) · FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2 (backend) · SQLite (`backend/data/suivi_budget.db`) · Docker Compose.

## Carte de la documentation

| Besoin | Où |
|---|---|
| Conventions backend / frontend | `backend/CLAUDE.md`, `frontend/src/CLAUDE.md` (chargés automatiquement dans ces dossiers) |
| Procédures détaillées | skills `.claude/skills/` : `numera-expert` (métier), `numera-backend`, `numera-frontend`, `numera-testing` |
| Discipline (obligatoire) | `numera-tdd` (test rouge avant tout code backend), `numera-clean-architecture` (où va le code, source unique, déplacements), `numera-finishing` (validation, docs, commit avant « terminé »), `numera-release` (quand et comment publier une version : choix patch/minor/major, tag), `numera-performance` (mesurer avant d'optimiser, N+1, lecture par colonnes, caches et leur invalidation, bundle, nginx) |
| Architecture, modèle de données, routes API | `ARCHITECTURE.md` |
| Workflow Git (PR, rulesets, branches de release) | `docs/WORKFLOW_GIT.md` |
| Scripts du dépôt (hors `backend/scripts/`, qui sert à l'exploitation du backend) | `scripts/quality/` (garde-fous à cliquet + `baselines/`), `scripts/release/`, `scripts/ci/`, `scripts/ops/` |
| Exploitation backend (logs, déploiement, sécurité) | `docs/BACKEND.md`, `backend/LOGGING.md`, `docs/BACKUP_RESTORE.md` |
| Centre d'Actions (audit, alertes budget, suggestions de règles) | `docs/ACTION_CENTER.md` |
| Serveur MCP | `mcp-server/README.md` |
| Guide agent historique (fichier local, ignoré par git) | `AGENT.MD` |

Quand le code change une route, un modèle, une commande ou une règle métier, mettre à jour `ARCHITECTURE.md` et, si besoin, le skill concerné dans le même commit.

**Jamais de tag flottant** : une action GitHub s'épingle par SHA de commit complet avec la version en commentaire (`actions/checkout@<sha40> # v4.4.0`), une image Docker par digest (`python:3.12-slim@sha256:…`), dans les `Dockerfile`, `docker-compose*.yml` et workflows. SHA obtenu par `git ls-remote --tags https://github.com/<org>/<action>`, digest par `docker buildx imagetools inspect <image>`. Contrôlé par `backend/tests/garde_fous/test_pinned_dependencies.py`.

**Git : PR obligatoire.** `main` et `release/**` sont protégées (rulesets `.github/rulesets/`, appliqués par `scripts/ci/github_rules.sh`) : plus de push direct. Branche `type/sujet` → PR au template `.github/pull_request_template.md` → checks `CI ok` + `Titre de PR` verts → merge en **squash** (le titre de PR, au format Conventional Commits, devient le commit et alimente les notes de version). Branches `release/X.Y` seulement à la demande, pour un correctif d'une ancienne version. Détail : `docs/WORKFLOW_GIT.md`.

**Performance** : toute optimisation suit le skill `numera-performance` — mesure sur jeu volumineux avant et après (`backend/scripts/perf_profile.py`), test de nombre de requêtes (fixture `measure_queries`), chiffres dans le message de commit. Pas de requête SQL dans une boucle, pas d'objets ORM pour une lecture seule volumineuse, pas d'`async def` sans `await`, pas de cache sans invalidation sur écriture.

**Releases** : tag `vX.Y.Z` sur `main` (ou `release/X.Y`) → `.github/workflows/release.yml` publie 3 images GHCR et la GitHub Release (notes auto depuis les commits Conventional Commits, `scripts/release/release_notes.py`). Décision et procédure : skill `numera-release` ; je release de moi-même quand les critères y sont réunis, ou sur demande. Des messages de commit propres = de bonnes notes.

## Commandes

> Python 3.14+ : pydantic-core incompatible. Utiliser Python 3.11 ou 3.12.

```bash
make backend-install       # uv sync (backend/.venv) ; dépendances : backend/pyproject.toml + uv.lock (mcp-server a les siens)
make setup                 # premier lancement (setup.sh), crée .env depuis .env.example
make dev                   # Docker : docker compose -f infra/docker-compose.yml up --build
make prod                  # infra/docker-compose.prod.yml
make test                  # pytest backend (backend/.venv si présent, sinon python3.12/3.11 ; PYTHON=... pour forcer)
make coverage              # tests + couverture avec seuil à cliquet : backend (backend/.coveragerc, 93 %) et frontend (frontend/vitest.config.ts, v8) ; ne jamais baisser un seuil
make lint / lint-fix       # ruff sur backend/ (règles : backend/ruff.toml), lint-fix corrige ce qui est sûr
make lint-front             # ESLint frontend (rules-of-hooks, exhaustive-deps, variables inutilisées) ; baseline frontend/eslint-baseline.json vide : zéro avertissement toléré
make typecheck             # mypy : strict sur app/domain et app/core, baseline à cliquet ailleurs (scripts/quality/baselines/mypy_baseline.json)
make check-size            # plafonds de taille (fichier/fonction), baseline à cliquet scripts/quality/baselines/code_size_baseline.json
make validate              # lint + lint-front + typecheck + check-size + coverage (tests backend et frontend avec seuils) + build frontend
make backend-seed-demo     # données de démo (backend/data/demo.db, jamais la vraie base)
make demo / demo-down      # instance de démo publique (infra/docker-compose.demo.yml, port 8090, demo/demo)
make test-e2e              # E2E Playwright (parcours utilisateur sur base de démo jetable, ~4 min) ; frontend/e2e/README.md
make backup-now            # backup dans le conteneur
cd backend && PYTHONPATH=. python3.11 scripts/perf_profile.py seed|bench|profile --db /tmp/perf_demo.db   # profilage sur base de démo volumineuse (skill numera-performance)
make release-check         # bump SemVer suggéré + aperçu des notes ; make release V=X.Y.Z crée et pousse le tag

# Dev local
cd backend && uvicorn app.main:app --reload --port 8001
cd frontend && npm run dev          # port 5173
cd frontend && npm test            # Vitest (jsdom + Testing Library + MSW) ; make test-front ; test:watch, coverage
cd frontend && npm run build        # tsc (app + tests) + vite build ; `npm run lint` (ESLint)
cd frontend && npm run typecheck    # tsc seul

# Un seul test
cd backend && PYTHONPATH=. python3.11 -m pytest tests/budget/test_tags.py -v   # PYTHONPATH=. requis
cd backend && PYTHONPATH=. python3.11 -m pytest tests/budget/test_tags.py::test_name -v
cd backend && PYTHONPATH=. python3.11 -m pytest tests -q     # suite complète : ~950 tests, ~80 s en parallèle (xdist, -n auto), ~2 min 40 en série

# Mot de passe admin (hash à mettre dans ADMIN_PASSWORD_HASH ; doubler les $ dans docker-compose)
python scripts/ops/change_password.py <mot-de-passe>
```

## Architecture

### Backend (`backend/app/`)
- `main.py` : lifespan (migrations Alembic + seed), middleware de logs, CORS via `settings.cors_origins` (pas `*`). Les routers sont dans la liste `protected_routers` et reçoivent tous `Depends(get_current_user)` (JWT) ; seuls `health` et `auth` sont publics. **Un nouveau router doit être ajouté à cette liste.**
- **Architecture en couches** (backend et frontend migrés, cf. `ARCHITECTURE.md` § Couches backend) : `controllers/` (controllers) → `services/` (cas d'usage, commit, erreurs métier `core/errors.py`) → `repositories/` (requêtes) / `domain/` (calculs purs) / `integrations/` (appels externes). Règles d'import vérifiées par `tests/garde_fous/test_architecture.py`, tailles par `scripts/quality/check_code_size.py` (baselines à cliquet : ne jamais les augmenter). Modèle à suivre : `accounts`. `controllers/`, `services/` et `repositories/` sont rangés par domaine, même arborescence dans les trois couches : `budget/`, `comptes/`, `investissement/`, `analytics/`, `audit/` (services), `systeme/` ; un controller n'importe pas un controller d'un autre domaine, `core/` n'importe que `core`, `models`, `db`. Code déplacé : supprimé de l'ancien emplacement, sans ré-export.
- `controllers/<domaine>/` : un router par sujet (`budget/transactions`, `comptes/accounts`, `investissement/holdings`, `systeme/auth`, …) ; `controllers/deps.py` à la racine. `controllers/analytics/` est un **package** (metrics, budget, investments, insights, reports, subscriptions, audit, diversity) ; budget, Centre d'Actions et projection de trésorerie sont calculés dans `services/analytics/` et `services/audit/` (registre de règles), les requêtes partagées dans `repositories/analytics/common.py`.
- `core/` : `config.py` (pydantic-settings, validation stricte des secrets en `APP_ENV=prod`), `security.py` + `login_rate_limit.py` (auth mono-utilisateur `ADMIN_USERNAME`/`ADMIN_PASSWORD_HASH` ; limiteurs `login_rate_limiter` / `totp_rate_limiter`), `errors.py` (erreurs métier), `logging.py`, `time.py`, `totp.py`, `mcp_tokens.py`, `migrations.py` (transverse uniquement). Valorisation des comptes titres : `services/investissement/portfolio/` ; positions : `services/investissement/holdings/` ; dividendes : `services/investissement/dividends.py`. Marché : `services/investissement/market/` + `integrations/yahoo_finance.py` ; profils ETF : `services/investissement/etf_profiles.py` (préréglages `domain/etf_presets.json`).
- `models/` (SQLAlchemy 2 `Mapped`/`mapped_column`), `schemas/` (Pydantic, `from_attributes=True`), `db/session.py`. Schéma modifié → nouvelle migration Alembic dans `backend/alembic/versions/`.
- Tests (`backend/tests/`) : `conftest.py` fixe `APP_ENV=test`, mot de passe admin `admin`, DB SQLite temporaire par test et override de `get_db`/`get_current_user`. Vérifier l'effet en base, pas seulement le code HTTP.

### Frontend (`frontend/src/`)
- `lib/api.ts` : `apiFetch()` + `api.get/post/patch/delete/upload` (JWT, `Content-Type: application/json` par défaut ; `api.upload` pour le multipart). Au-dessus, `lib/api/<domaine>.ts` (`accounts`, `analytics`, `classement`, `investments`, `loans`, `monthReview`, `recurring`, `reimbursements`, `savings`, `settings`, `transactions`) : une fonction typée par route, seul moyen d'appeler l'API depuis les pages et composants (jamais `api.get(...)` direct, garde-fou `noDirectApi.test.ts`).
- `pages/` (une par route, react-router v7 dans `App.tsx`, protégé par `components/layout/ProtectedRoute`) ; composants par domaine dans `components/{analytics,dashboard,investments,settings,tools,layout}` ; primitives shadcn/Radix dans `components/ui`. `Dashboard` est découpé via `components/dashboard/tabs` et le hook `useDashboardData`.

### Serveur MCP (`mcp-server/`)
**Lecture seule.** Point d'entrée `server.py`, code dans le package `numera_mcp/` : `tools/<domaine>.py` (un module par domaine du backend, chacun expose `register(mcp)`), `resources.py`, `prompts.py`, `api_client.py` (proxy de l'API FastAPI authentifié par token MCP généré dans Paramètres → Sécurité, exposé sur `/mcp` par Nginx ; 48 outils, KPI calculés par le backend), `auth.py`, `config.py`, `formatting.py`. Plus de mode SQLite direct. L'API refuse toute méthode autre que `GET` avec un token MCP : ne pas ajouter d'outil d'écriture. Clients : Claude Code (`claude mcp add --transport http`) et Claude Desktop (pont `mcp-remote`). Détails : `mcp-server/README.md`. Toute nouvelle route de lecture exposable doit être répercutée dans `numera_mcp/tools/<domaine>.py` puis le snapshot `mcp-server/tests/surface_snapshot.json` régénéré (`python -m tests.regen_snapshot`). Tests et lint : `cd mcp-server && uv run --with pytest python -m pytest tests -q` ; `make lint` couvre aussi `mcp-server/` ; `check_code_size.py` aussi.

## Modèle de données

- `accounts.type` : `courant`, `epargne`, `investissement`, `assurance_vie` (validé à la création/modification ; un ancien type inconnu reste lisible).
- `transactions.type` : `Entree`, `Sortie`, `Interets`, `Solde Initial` (base du solde, exclue des KPI revenus/dépenses).
- `investment_transactions.type` : `versement`, `retrait`, `achat`, `vente`, `frais`, `dividende` (dividende non compté dans le montant investi). Valeur d'un compte titres = positions × cours + espèces (`services/investissement/portfolio/`).
- Positions titres : `portfolio_holding` / `controllers/investissement/holdings.py` ; profils ETF : `etf_profile`.

## Règles métier critiques

1. Montants **toujours positifs** ; le sens est porté par `type`.
2. **KPI calculés côté backend uniquement** (`controllers/analytics/`), jamais côté frontend.
3. `running_balance` recalculé intégralement après toute création/modification/suppression (`recalculate_running_balances` dans `services/budget/balances.py`).
4. Import CSV **idempotent** : doublon = `(account_id, date, amount, merchant, type)`. Le commit insère avec un solde courant partant de la dernière transaction, puis appelle `recalculate_running_balances` si au moins une ligne est importée (les soldes sont donc corrects même pour des données antérieures).
5. Un seul `is_zero_point = True` par compte investissement.
6. Salaire (`services/budget/salary_generation.py`, montant `domain/salary.py::salary_amount`) : **une seule** transaction `Entree` « Salaire » = `net_salary − (nb jours TT × ticket_employee_share)`, rattachée à la récurrence salaire. Les tickets restaurant sont informatifs, aucune transaction TR n'est créée. Génération idempotente (`SalaryMonth.is_generated`).
7. Normalisation marchands : `merchant_id` relie à un marchand canonique sans modifier le libellé bancaire `merchant`.
8. Vérification de compte : `last_verified_at` mis à jour par validation explicite.
9. `normalize_transaction_type()` mappe `"type"` → `"Solde Initial"` volontairement (export Numbers).
10. Revue de fin de mois (`/month-review`) : clôturer = **marquer**, jamais verrouiller ; `transactions.is_exceptional` reste dans les totaux officiels et les soldes, seules les lectures « hors exceptionnel » (rapport mensuel, revue) l'isolent.

11. **Revenu** = entrées sur un compte `courant` (+ intérêts) ; une entrée sur un autre compte n'en est un que si sa catégorie est de type `revenu` (`income_criterion`, `repositories/analytics/common.py`). Même définition dans budget, money-flow, Sankey, kpi-history, timeseries. **Patrimoine** = tous les comptes actifs, tous types, via `services/comptes/wealth.py::account_values` (source unique).

12. **Transaction à venir** (datée après aujourd'hui) : elle est stockée avec son `running_balance` chronologique, mais ne compte qu'à sa date. Tout solde « courant » lit la dernière transaction **avant `core.time.end_of_today()`** (demain 00:00, granularité au jour) ; tout total de période passe par `budget_period.period_bounds` (fenêtre arrêtée à aujourd'hui) et non `period_window` (fenêtre entière, pour l'affichage des dates). Jamais de `datetime.now()` ni de « dernier `running_balance` » brut pour un solde courant. `end` d'une période et `end_of_today()` sont des bornes **exclusives** : toujours `date < end`, jamais `<=` (garde-fou `tests/garde_fous/test_end_bounds_guard.py`) ; `account_values(at=…)` suit la même convention (défaut `end_of_today()`).

Pipeline import : détection du délimiteur (`,` `;` `\t`) → en-têtes normalisés via `HEADER_ALIASES` → mapping catégories (manuel puis auto-création si `create_missing_categories=True`) → détection doublons → insert + log dans `imports_log`.

Multi-devises : Frankfurter, taux courants cachés 6 h en mémoire, historiques en base (`historical_exchange_rates`), fallback offline `EUR=1.0, USD=1.08, GBP=0.84, CHF=0.95`. Passer par `services/comptes/exchange_rates.py::convert_amount` (taux datés mis en cache en base, sans commit : l'appelant valide) / `integrations/currency.py::get_exchange_rates` (async). Stocker `amount` (devise du compte) + `original_amount` et `currency` (saisie d'origine).

## Outils MCP Distill (préférences du projet)

- Exploration de code : `mcp__distill__smart_file_read` (avec `target` pour une fonction/classe). Utiliser `Read` natif avant un `Edit` et pour les fichiers de config/`.md`/`.env`.
- Sortie Bash volumineuse (>500 car.) : `mcp__distill__auto_optimize`.
- Opérations multi-étapes : `mcp__distill__code_execute` (SDK `ctx.files/code/git/search/analyze/compress`).
- Ne pas envoyer de fichiers entiers sans nécessité ; préférer symboles, fonctions et diffs.
