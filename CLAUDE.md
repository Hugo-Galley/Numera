# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**Self-hosted** web application for budget and investment tracking ("Numera" / "Suivi Budget"), personal single-user use. Replaces a Numbers spreadsheet. Local data (SQLite); the only outbound calls are Frankfurter (exchange rates), market data (Yahoo Finance: `integrations/yahoo_finance.py`, through `services/investissement/market/`) and, only if the user makes use of them, ntfy / Telegram for notifications (`services/systeme/notifications.py`, channels: `integrations/notifications.py`), Google's favicon service for the logo of a domain (`integrations/logos.py`), a private GitHub repository for uploading encrypted backups (`backend/scripts/git_sync.py`); on the browser side, the world map's base layer comes from `unpkg.com` (`components/ui/WorldMap.tsx`, the only third-party origin in the CSP). Reference list: `ARCHITECTURE.md` (overview).

Stack: React 19 + Vite 8 (Rolldown) + TypeScript + Tailwind 4 (CSS-first config in `frontend/src/styles.css`, no more `tailwind.config.js`) + Recharts (frontend) · FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2 (backend) · SQLite (`backend/data/suivi_budget.db`) · Docker Compose.

**Language.** Documentation, skills, `CLAUDE.md` files and commit/PR titles are written in **English**. The user interface is translated (French reference, English, Spanish: see `frontend/src/CLAUDE.md` § Languages and `backend/CLAUDE.md`). The domain vocabulary stored in the database and in the code (`Entree`, `Sortie`, `Solde Initial`, `courant`, `epargne`, folder names such as `comptes/` or `investissement/`) are still **French**: keep these identifiers exactly as they are, and gloss them in English in docs when helpful.

## Documentation map

| Need | Where |
|---|---|
| Backend / frontend conventions | `backend/CLAUDE.md`, `frontend/src/CLAUDE.md` (loaded automatically in those folders) |
| Detailed procedures | skills in `.claude/skills/`: `numera-expert` (business domain), `numera-backend`, `numera-frontend`, `numera-testing` |
| Discipline (mandatory) | `numera-tdd` (failing test before any backend code), `numera-clean-architecture` (where code goes, single source, moves), `numera-finishing` (validation, docs, commit before "done"), `numera-release` (when and how to publish a version: patch/minor/major choice, tag), `numera-performance` (measure before optimising, N+1, column reads, caches and their invalidation, bundle, nginx) |
| Architecture, data model, API routes | `ARCHITECTURE.md` |
| Git workflow (PRs, rulesets, release branches) | `docs/WORKFLOW_GIT.md` |
| Backend operations (logs, deployment, security) | `docs/BACKEND.md`, `backend/LOGGING.md`, `docs/BACKUP_RESTORE.md` |
| Action Center (audit, budget alerts, rule suggestions) | `docs/ACTION_CENTER.md` |
| MCP server | `mcp-server/README.md` |
| Legacy agent guide (local file, ignored by git) | `AGENT.MD` |
| Repository scripts (apart from `backend/scripts/`, which serves backend operations) | `scripts/quality/` (ratchet safeguards + `baselines/`), `scripts/release/`, `scripts/ci/`, `scripts/ops/` |

When code changes a route, a model, a command or a business rule, update `ARCHITECTURE.md` and, if needed, the relevant skill in the same commit.

**Never a floating tag**: a GitHub Action is pinned by full commit SHA with the version in a comment (`actions/checkout@<sha40> # v4.4.0`), a Docker image by digest (`python:3.12-slim@sha256:…`), in the `Dockerfile`s, `docker-compose*.yml` and workflows. Get the SHA with `git ls-remote --tags https://github.com/<org>/<action>`, the digest with `docker buildx imagetools inspect <image>`. Checked by `backend/tests/garde_fous/test_pinned_dependencies.py`.

**Git: PRs are mandatory.** `main` and `release/**` are protected (rulesets in `.github/rulesets/`, applied by `scripts/ci/github_rules.sh`): no more direct pushes. Branch `type/topic` → PR using the template `.github/pull_request_template.md` → green `CI ok` + `Titre de PR` (PR title) checks → **squash** merge (the PR title, in Conventional Commits format, becomes the commit and feeds the release notes). `release/X.Y` branches only on demand, for a fix to an older version. Details: `docs/WORKFLOW_GIT.md`.

**Performance**: every optimisation follows the `numera-performance` skill — measurement on a large dataset before and after (`backend/scripts/perf_profile.py`), a query-count test (`measure_queries` fixture), figures in the commit message. No SQL query in a loop, no ORM objects for a large read-only load, no `async def` without `await`, no cache without invalidation on write.

**Releases**: tag `vX.Y.Z` on `main` (or `release/X.Y`) → `.github/workflows/release.yml` publishes 3 GHCR images and the GitHub Release (automatic notes from Conventional Commits, `scripts/release/release_notes.py`). Decision and procedure: `numera-release` skill; I release on my own when its criteria are met, or on request. Clean commit messages = good notes.

## Commands

> Python 3.14+: pydantic-core incompatible. Use Python 3.11 or 3.12.

```bash
make backend-install       # uv sync (backend/.venv); dependencies: backend/pyproject.toml + uv.lock (mcp-server has its own)
make setup                 # first run (setup.sh), creates .env from .env.example
make dev                   # Docker: docker compose -f infra/docker-compose.yml up --build
make prod                  # infra/docker-compose.prod.yml
make test                  # backend pytest (backend/.venv if present, otherwise python3.12/3.11; PYTHON=... to force)
make coverage              # tests + coverage with ratchet threshold: backend (backend/.coveragerc, 93 %) and frontend (frontend/vitest.config.ts, v8); never lower a threshold
make lint / lint-fix       # ruff on backend/ (rules: backend/ruff.toml), lint-fix fixes what is safe
make lint-front             # frontend ESLint (rules-of-hooks, exhaustive-deps, unused variables); baseline frontend/eslint-baseline.json empty: zero warnings tolerated
make typecheck             # mypy strict on the whole of backend/app (backend/mypy.ini), zero errors tolerated
make check-size            # size caps (file/function), ratchet baseline scripts/quality/baselines/code_size_baseline.json
make validate              # lint + lint-front + typecheck + check-size + coverage (backend and frontend tests with thresholds) + frontend build
make backend-seed-demo     # demo data (backend/data/demo.db, never the real database)
make demo / demo-down      # public demo instance (infra/docker-compose.demo.yml, port 8090, demo/demo)
make test-e2e              # Playwright E2E (user journeys on a throwaway demo database + `security` profile on a non-demo database: 2FA, passkeys, MCP tokens, backup, notifications; ~5 min); frontend/e2e/README.md
make backup-now            # backup inside the container
cd backend && PYTHONPATH=. python3.11 scripts/perf_profile.py seed|bench|profile --db /tmp/perf_demo.db   # profiling on a large demo database (numera-performance skill)
make release-check         # suggested SemVer bump + notes preview; make release V=X.Y.Z creates and pushes the tag

# Local dev
cd backend && uvicorn app.main:app --reload --port 8001
cd frontend && npm run dev          # port 5173
cd frontend && npm test            # Vitest (jsdom + Testing Library + MSW); make test-front; test:watch, coverage
cd frontend && npm run build        # tsc (app + tests) + vite build; `npm run lint` (ESLint)
cd frontend && npm run typecheck    # tsc only

# A single test
cd backend && PYTHONPATH=. python3.11 -m pytest tests/budget/test_tags.py -v   # PYTHONPATH=. required
cd backend && PYTHONPATH=. python3.11 -m pytest tests/budget/test_tags.py::test_name -v
cd backend && PYTHONPATH=. python3.11 -m pytest tests -q     # full suite: ~1240 tests, ~90 s in parallel (xdist, -n auto), ~2 min 40 serially

# Admin password (hash to put in ADMIN_PASSWORD_HASH; double the $ in docker-compose)
python scripts/ops/change_password.py <password>
```

## Architecture

### Backend (`backend/app/`)
- `main.py`: lifespan (Alembic migrations + seed), logging middleware, CORS through `settings.cors_origins` (not `*`). Routers are in the `protected_routers` list and all receive `Depends(get_current_user)` (JWT); the only public routes are `health`, the login routes under `/auth` (`auth`, `passkeys`, `totp`: each management route there requires `get_current_user` itself) and `GET /logos/img/{ref}` (an `<img>` tag does not send the JWT). **A new router must be added to this list.**
- **Layered architecture** (backend and frontend migrated, see `ARCHITECTURE.md` § Backend layers): `controllers/` (controllers) → `services/` (use cases, commit, business errors `core/errors.py`) → `repositories/` (queries) / `domain/` (pure calculations) / `integrations/` (external calls). Import rules checked by `tests/garde_fous/test_architecture.py`, sizes by `scripts/quality/check_code_size.py` (ratchet baselines: never raise them). Model to follow: `accounts`. `controllers/`, `services/` and `repositories/` are organised by domain, same tree in the three layers: `budget/`, `comptes/` (accounts), `investissement/` (investments), `analytics/`, `audit/` (services), `systeme/` (system); a controller does not import a controller of another domain, `core/` only imports `core`, `models`, `db`. Moved code: deleted from the old location, no re-export.
- `controllers/<domain>/`: one router per subject (`budget/transactions`, `comptes/accounts`, `investissement/holdings`, `systeme/auth`, …); `controllers/deps.py` at the root. `controllers/analytics/` is a **package** (metrics, budget, investments, insights, reports, subscriptions, audit, diversity); budget, Action Center and cash-flow projection are computed in `services/analytics/` and `services/audit/` (rule registry), shared queries in `repositories/analytics/common.py`.
- `core/`: `config.py` (pydantic-settings, strict secret validation when `APP_ENV=prod`), `security.py` + `login_rate_limit.py` (single-user auth `ADMIN_USERNAME`/`ADMIN_PASSWORD_HASH`; limiters `login_rate_limiter` / `totp_rate_limiter`), `errors.py` (business errors), `logging.py`, `time.py`, `totp.py`, `mcp_tokens.py`, `migrations.py` (cross-cutting only). Brokerage-account valuation: `services/investissement/portfolio/`; positions: `services/investissement/holdings/`; dividends: `services/investissement/dividends.py`. Market: `services/investissement/market/` + `integrations/yahoo_finance.py`; ETF profiles: `services/investissement/etf_profiles.py` (presets `domain/etf_presets.json`).
- `models/` (SQLAlchemy 2 `Mapped`/`mapped_column`), `schemas/` (Pydantic, `from_attributes=True`), `db/session.py`. Schema changed → new Alembic migration in `backend/alembic/versions/`.
- Tests (`backend/tests/`): `conftest.py` sets `APP_ENV=test`, admin password `admin`, a temporary SQLite DB per test and overrides `get_db`/`get_current_user`. Check the effect in the database, not only the HTTP code.

### Frontend (`frontend/src/`)
- `lib/api.ts`: `apiFetch()` + `api.get/post/patch/delete/upload` (JWT, `Content-Type: application/json` by default; `api.upload` for multipart). On top, `lib/api/<domain>.ts` (`accounts`, `analytics`, `classement`, `investments`, `loans`, `monthReview`, `recurring`, `reimbursements`, `savings`, `settings`, `transactions`): one typed function per route, the only way to call the API from pages and components (never a direct `api.get(...)`, safeguard `noDirectApi.test.ts`).
- `pages/` (one per route, react-router v7 in `App.tsx`, protected by `components/layout/ProtectedRoute`); components by domain in `components/{analytics,dashboard,investments,settings,tools,layout}`; shadcn/Radix primitives in `components/ui`. `Dashboard` is split through `components/dashboard/tabs` and the `useDashboardData` hook.

### MCP server (`mcp-server/`)
**Read-only.** Entry point `server.py`, code in the `numera_mcp/` package: `tools/<domain>.py` (one module per backend domain, each exposes `register(mcp)`), `resources.py`, `prompts.py`, `api_client.py` (proxy of the FastAPI API authenticated by an MCP token generated in Settings → Security (*Paramètres → Sécurité*), exposed on `/mcp` by Nginx; 48 tools, KPIs computed by the backend), `auth.py`, `config.py`, `formatting.py`. No more direct SQLite mode. The API refuses any method other than `GET` with an MCP token: do not add a write tool. Clients: Claude Code (`claude mcp add --transport http`) and Claude Desktop (`mcp-remote` bridge). Details: `mcp-server/README.md`. Every new exposable read route must be mirrored in `numera_mcp/tools/<domain>.py`, then the snapshot `mcp-server/tests/surface_snapshot.json` regenerated (`python -m tests.regen_snapshot`). Tests and lint: `cd mcp-server && uv run --with pytest python -m pytest tests -q`; `make lint` also covers `mcp-server/`; so does `check_code_size.py`.

## Data model

- `accounts.type`: `courant` (current/checking), `epargne` (savings), `investissement` (investment), `assurance_vie` (life insurance) (validated on create/update; an old unknown type stays readable).
- `transactions.type`: `Entree` (income/inflow), `Sortie` (expense/outflow), `Interets` (interest), `Solde Initial` (opening balance: base of the balance, excluded from income/expense KPIs).
- `investment_transactions.type`: `versement` (deposit), `retrait` (withdrawal), `achat` (buy), `vente` (sell), `frais` (fees), `dividende` (dividend; not counted in the invested amount). Value of a securities account = positions × price + cash (`services/investissement/portfolio/`).
- Security positions: `portfolio_holding` / `controllers/investissement/holdings.py`; ETF profiles: `etf_profile`.

## Critical business rules

1. Amounts are **always positive**; the direction is carried by `type`.
2. **KPIs are computed on the backend only** (`controllers/analytics/`), never on the frontend.
3. `running_balance` is fully recomputed after any creation/modification/deletion (`recalculate_running_balances` in `services/budget/balances.py`).
4. CSV import is **idempotent**: duplicate = `(account_id, date, amount, merchant, type)`. The commit inserts with a running balance starting from the last transaction, then calls `recalculate_running_balances` if at least one row is imported (so balances are correct even for earlier data).
5. A single `is_zero_point = True` per investment account.
6. Salary (`services/budget/salary_generation.py`, amount `domain/salary.py::salary_amount`): **a single** `Entree` transaction "Salaire" (salary) = `net_salary − (number of remote-work days × ticket_employee_share)`, attached to the salary recurrence. Meal vouchers are informational, no voucher transaction is created. Idempotent generation (`SalaryMonth.is_generated`).
7. Merchant normalisation: `merchant_id` links to a canonical merchant without changing the bank label `merchant`.
8. Account verification: `last_verified_at` is updated by explicit validation.
9. `normalize_transaction_type()` maps `"type"` → `"Solde Initial"` on purpose (Numbers export).
10. End-of-month review (`/month-review`): closing = **marking**, never locking; `transactions.is_exceptional` stays in the official totals and balances, only the "excluding exceptional" reads (monthly report, review) isolate it.

11. **Income** = inflows on a `courant` account (+ interest); an inflow on another account only counts as income if its category is of type `revenu` (`income_criterion`, `repositories/analytics/common.py`). Same definition in budget, money-flow, Sankey, kpi-history, timeseries. **Net worth** (*patrimoine*) = all active accounts, all types, through `services/comptes/wealth.py::account_values` (single source).

12. **Upcoming transaction** (dated after today): it is stored with its chronological `running_balance`, but only counts on its date. Any "current" balance reads the last transaction **before `core.time.end_of_today()`** (tomorrow 00:00, day granularity); any period total goes through `budget_period.period_bounds` (window capped at today) and not `period_window` (whole window, for displaying dates). Never `datetime.now()` nor a raw "last `running_balance`" for a current balance. A period's `end` and `end_of_today()` are **exclusive** bounds: always `date < end`, never `<=` (guard `tests/garde_fous/test_end_bounds_guard.py`); `account_values(at=…)` follows the same convention (default `end_of_today()`).

Import pipeline: delimiter detection (`,` `;` `\t`) → headers normalised through `HEADER_ALIASES` → category mapping (manual, then auto-creation if `create_missing_categories=True`) → duplicate detection → insert + log in `imports_log`.

Multi-currency: Frankfurter, current rates cached 6 h in memory, historical ones in the database (`historical_exchange_rates`), offline fallback `EUR=1.0, USD=1.08, GBP=0.84, CHF=0.95`. Go through `services/comptes/exchange_rates.py::convert_amount` (dated rates cached in the database, without commit: the caller commits) / `integrations/currency.py::get_exchange_rates` (async). Store `amount` (account currency) + `original_amount` and `currency` (original entry).

## Distill MCP tools (project preferences)

- Code exploration: `mcp__distill__smart_file_read` (with `target` for a function/class). Use native `Read` before an `Edit` and for config/`.md`/`.env` files.
- Large Bash output (>500 chars): `mcp__distill__auto_optimize`.
- Multi-step operations: `mcp__distill__code_execute` (SDK `ctx.files/code/git/search/analyze/compress`).
- Do not send whole files without need; prefer symbols, functions and diffs.
