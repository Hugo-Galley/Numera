---
name: numera-backend
description: Procedures for modifying the Numera backend (FastAPI, SQLAlchemy 2, Alembic, Pydantic v2): adding an endpoint or a router, a model + migration, an analytics KPI, a background task. Load as soon as editing backend/app/.
---

# Numera backend — procedures

Conventions and pitfalls: `backend/CLAUDE.md` (read first). Business rules: `numera-expert` skill. Code that reads many rows, loops over the database or caches: `numera-performance` skill. Every procedure below starts with a failing test (`numera-tdd`); where to put code and how to move it: `numera-clean-architecture`.

## Adding an endpoint to an existing router

1. `Create` / `Update` / `Read` schemas in `app/schemas/<domain>.py` (`ConfigDict(from_attributes=True)` on `Read`).
2. Queries in `app/repositories/<domain>/<subject>.py` (no `commit`), logic in `app/services/<domain>/<subject>.py` (commit, `NotFoundError`/`BusinessRuleError`/`ConflictError` from `app.core.errors`, never `HTTPException`), pure calculation in `app/domain/`. Model: `accounts` (`comptes/accounts.py` in the three layers). Domains: `budget`, `comptes`, `investissement`, `analytics`, `audit` (services), `systeme`; same tree in the three layers.
3. Endpoint in `app/controllers/<domain>/<subject>.py`: `response_model`, `db: Session = Depends(get_db)`, one line that calls the service. No `Depends(get_current_user)` to add: the router is already protected in `main.py`.
4. Transaction mutation → `recalculate_running_balances(db, account_id)` (`app.services.budget.balances`) for each account touched, **then `db.commit()`**: the recomputation only does a `flush`.
5. FastAPI route order: declare fixed paths (`/bulk`, `/merchants`, `/potential-transfers`, `/auto-normalize`) **before** `/{id}`.
6. Tests: service (`db_session`, no HTTP) and route (`client`) in `backend/tests/<domain>/test_<subject>.py`. `tests/garde_fous/test_architecture.py` (a controller does not import another domain's controller) and `scripts/quality/check_code_size.py` must stay green.
7. Update `ARCHITECTURE.md` (routes) and, if the MCP server exposes the domain, `mcp-server/numera_mcp/tools/<domain>.py`.

## Adding a new router

Create `app/controllers/<domain>/<name>.py` (`APIRouter(prefix="/<name>", tags=[...])`, with its `services/<domain>/<name>.py` and `repositories/<domain>/<name>.py`), import it in `app/main.py` **and** add it to `protected_routers`. Without that the route does not exist / or is not protected.

## Changing the database schema

1. Model in `app/models/` (new file → import it in `app/models/__init__.py`, otherwise Alembic and the tests do not see it).
2. `cd backend && alembic revision --autogenerate -m "description"`; review the generated file in `alembic/versions/` (SQLite: `batch_alter_table` to alter/drop columns).
3. Migrations run at startup (`core/migrations.py`); test locally with `alembic upgrade head` on a copy of the database.

## Adding a KPI / chart

1. Calculation in `app/services/analytics/` (new KPI) (route in `app/controllers/analytics/`, one line that calls the service); shared queries: `app/repositories/analytics/common.py` (`NET_AMOUNT`, `income_criterion`, `category_lines`…), pure calculations: `app/domain/`. Call another KPI through its service (`compute_budget`…), never through a route function. Never move the calculation to the frontend.
2. Response schema in `app/schemas/insight.py` (or `investment.py`) and `response_model`.
3. Respect: exclusion of `Solde Initial` from income/expenses, exclusion of internal transfers for "real expenses", `account_id` / `month` / `year` filters consistent with the neighbouring endpoints.
4. Test in `tests/` (see `test_import_and_analytics.py`, `test_money_flow.py`, `test_sankey.py`), then consume the endpoint in the frontend.

## Adding an action type to the Action Center

Create `services/audit/rules/<name>.py` with `detect(ctx)`, add it to `RULES` (`services/audit/__init__.py`); queries in `repositories/analytics/audit.py`. Details: `docs/ACTION_CENTER.md`; `ActionItem.id` must be deterministic.

## Background task

`recurring_transactions_task` in `app/main.py` (every hour). Add periodic work there rather than creating a new loop; open/close your own `SessionLocal()`.

## Do not

- `db.execute(text(...))` except for a performance need.
- Business logic in models.
- Log/return `SECRET_KEY`, a password hash, a JWT.
- Outbound network calls other than Frankfurter / Yahoo Finance / notification channels enabled by the user (ntfy, Telegram); any new external dependency must be discussed (local-first principle).
- Modify the `*.db` database directly or commit it.
