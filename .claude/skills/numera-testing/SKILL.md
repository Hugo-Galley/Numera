---
name: numera-testing
description: How to run, write and debug Numera's tests (backend pytest, frontend Vitest) and what to check before considering a task done. Load before any validation or to fix a failing test.
---

# Numera — tests and validation

## Running backend tests

From `backend/` (`PYTHONPATH` is mandatory, otherwise `ModuleNotFoundError: app`):

```bash
PYTHONPATH=. python3.11 -m pytest tests -q                       # everything: ~950 tests, ~2 min 40 serially; add -n auto (pytest-xdist): ~80 s
PYTHONPATH=. python3.11 -m pytest tests/budget/test_merchants.py -v     # one file
PYTHONPATH=. python3.11 -m pytest tests/budget/test_tags.py::test_x -v  # one test
```

- `make test` / `make validate` pick the interpreter automatically: `backend/.venv/bin/python` (created by `make backend-install`, i.e. `uv sync`), then the old `backend/venv`, otherwise `python3.12`, otherwise `python3.11` (overridable: `make test PYTHON=...`). `backend/venv_new` is Python 3.14 without pytest, and pydantic-core does not support 3.14.
- Dependencies: `backend/pyproject.toml` + `backend/uv.lock` (`dev` group for pytest/ruff/mypy). Adding a dependency: `cd backend && uv add <pkg>` (or `uv add --dev`), commit `uv.lock`.

## Layout (`backend/tests/`)

One folder per domain, like `app/services/`: `budget/`, `comptes/`, `investissement/`, `analytics/`, `audit/`, `systeme/`, plus `garde_fous/` (architecture, sizes, migrations, routes, pinning, network) and `non_regression/` (snapshots, cross-cutting audit batches). `conftest.py` and `snapshots/` at the root. Run one domain: `PYTHONPATH=. python3.11 -m pytest tests/budget -q`. Unique file names (no `__init__.py`).

## Test infrastructure (`tests/conftest.py`)

- `APP_ENV=test`: no migrations or seed at startup; tables created by `Base.metadata.create_all` on a temporary SQLite (`tmp_path`) specific to each test.
- `ADMIN_PASSWORD_HASH` set to the password `admin`.
- Fixtures: `db_session` (Session) and `client` (TestClient with `get_db` — two import paths — and `get_current_user` overridden; the login rate limiter is reset).
- A `401` in a test almost always means `client` is not used or the override is not active.
- `database is locked`: another process keeps the database open.

## Writing a test

The test is written **before** the code and must be seen failing (`numera-tdd` skill, which also says which level to choose: `domain`, service, route). File `tests/<domain>/test_<subject>.py`. Create the data through `db_session` or the API (`client.post`), call the endpoint, check the HTTP code **and** the state in the database (balances, flags, links). One test per fixed bug.

## Checkpoints depending on the change

- Transactions: consistent `running_balance` after create/update/delete/bulk/import (`test_import_and_analytics.py`, `test_transfers.py`).
- Currencies: `original_amount` + `currency` kept, `amount` converted to the account currency.
- Merchants / rules / tags: `test_merchants.py`, `test_categorization_rules.py`, `test_tags.py`.
- Salary: single "Salaire" transaction, `is_generated` set, no duplicate (see `test_p0_features.py`).
- Action Center / audit: the resolved issue disappears from `/analytics/actions` (`test_data_audit.py`, `test_anomaly_detection.py`).
- Analytics, non-regression net: `tests/non_regression/test_analytics_snapshots.py` compares the JSON output of all analytics routes (budget, Action Center, metrics, reports, insights, subscriptions, yearly review, investments, projections, taxation, month review) with the snapshots in `tests/snapshots/analytics/`, on the demo data at a frozen date (`freezegun`, 2026-06-15 10:00) completed to trigger each Action Center rule. A difference is a bug: **never regenerate the snapshots to make the test pass**. Deliberate regeneration only for an intended figure change justified in the commit: `UPDATE_SNAPSHOTS=1 PYTHONPATH=. python3.11 -m pytest tests/non_regression/test_analytics_snapshots.py`.
- Portfolio, same principle: `tests/non_regression/test_portfolio_snapshots.py` (reuses the fixture above and adds a securities account "CTO Instantané" with Zero Point, purchase, USD sale, fees, dividend with withholding and broker statements) freezes `/analytics/portfolio[/{id}]`, `/analytics/dividends`, `/holdings`, `/holdings/estimate-costs`, `/investment-transactions`, `/analytics/diversity-scanner`, `/etf-profiles` and the broker reconciliation (`/analytics/actions`) in `tests/snapshots/portfolio/`. Yahoo calls are neutralised by patching `integrations/yahoo_finance.py` (`fetch_chart`, `fetch_composition`), never by disabling `block_network`.
- Analytics: `test_money_flow.py`, `test_sankey.py`, `test_cashflow_projection.py`, `test_asset_allocation.py`, `test_diversity_scanner.py`, `test_simulation.py`, `test_subscriptions.py`, `test_savings_goals.py`, `test_calendar.py`, `test_excluded_months.py`, `test_filtering.py`.
- Auth / config: `test_auth.py`, `test_config.py`.

## Frontend

```bash
cd frontend && npm test                                   # everything (vitest run); make test-front from the root
cd frontend && npx vitest run src/lib/utils.test.ts       # one file
cd frontend && npx vitest run -t "formatCurrency"         # by test name
cd frontend && npm run test:watch                         # continuous
cd frontend && npm run build                              # tsc app + tests (0 errors), then vite build
```

Both are mandatory: `npm test` does not check types, the build does not run the tests. Conventions (location `X.test.tsx`, `renderWithProviders`, MSW handlers per domain, factories, frozen clock): `frontend/src/CLAUDE.md` § Verification.

Debugging: "Requête(s) sans handler MSW : GET …" (request(s) without an MSW handler) = add a handler (`server.use(...)` in the test, or `src/test/handlers/<domain>.ts`); `localStorage` undefined under Node ≥ 25 = run through `npm test` / `vitest.config.ts` (option `--no-experimental-webstorage`); an element not found: `screen.debug()`, and `findBy…` for what appears after a request. E2E (Playwright, `make test-e2e`, critical journeys on a throwaway demo database): `frontend/e2e/README.md`. Additional manual checks: privacy mode, toasts, dark theme, mobile.

## Definition of "done"

Full checklist (validation depending on the change, docs, commit): `numera-finishing` skill.
