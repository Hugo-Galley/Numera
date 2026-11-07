# ARCHITECTURE.md

## Purpose

Describe the repository's current architecture so that a human or an AI agent can modify the project without guessing the real organisation.

Language note: prose is in English; identifiers, routes, database values and UI labels that exist in French in the code (`Entree`, `Sortie`, `epargne_realisee`, "Échéances"…) are kept verbatim and glossed where useful.

## Overview

- Frontend: React 19 + Vite 8 + TypeScript + Tailwind + Recharts SPA.
- Backend: FastAPI + SQLAlchemy + Alembic + Pydantic v2.
- Database: local SQLite in `backend/data/suivi_budget.db` in Docker dev.
- Auth: single-admin JWT, business routes protected; MCP tokens (`nmr_…`) accepted in place of the JWT, read-only (`GET`), never on `/admin`.
- Orchestration: `infra/docker-compose.yml` (dev: `backend`, `frontend`, `backup`); `infra/docker-compose.prod.yml` (prod: + `mcp-server` in streamable-http; non-root Nginx frontend (8080 in the container) published on `127.0.0.1:8082`, proxy `/api/` → `backend:8001` and `/mcp` → `mcp-server:8100`).
- External services (the only outbound calls): Frankfurter (exchange rates) and Yahoo Finance (security search/quotes, ETF profiles).
- MCP server in `mcp-server/`, read-only, connected to Claude Code / Claude Desktop through a token generated in Settings → Security (see `mcp-server/README.md`).

Main flow:

1. The user logs in through `/login`.
2. The frontend stores the token in `localStorage`.
3. `apiFetch()` adds the bearer token to JSON calls.
4. FastAPI validates the user through `get_current_user`.
5. Endpoints read/write SQLite through SQLAlchemy.
6. Financial aggregates are computed by the backend and returned ready to display.

## Actual tree

```text
backend/
  alembic/              migrations
  app/
    controllers/        REST routers (formerly api/), one package per domain + deps.py (get_current_user; `get_db` is re-exported there from db/session.py: a single session per request)
    services/           use cases, same tree by domain
    repositories/       SQLAlchemy queries, same tree by domain, no commit
                        budget/          transactions (+ transaction_writes/links, splits, balances), categories,
                                         categorization_rules, merchants, tags, imports, exports, recurring(_transactions),
                                         salary (+ salary_generation, work_time), transfer_rules, transfers,
                                         reimbursements, provisions, benefits, savings_goals, month_review, budget_period,
                                         subscription_prices
                        comptes/         accounts, balance_snapshots, reconciliation, loans, financial_events, wealth
                        investissement/  investment_transactions, holdings/ (replay, inventory), etf_profiles,
                                         market/ (prices, search), tax, dividends, portfolio/ (valuation),
                                         security_prices
                        analytics/       budget/, metrics/, reports/, investments/, portfolio, dividends, diversity, ...
                                         (controllers: sub-routers mounted under /analytics, including audit)
                        audit/           services only: Action Center (rule registry)
                        systeme/         auth, totp, passkeys, admin, notifications, logos, health, seeds, demo/
    domain/             pure calculations: finance, transactions, budget, metrics, projections, tax, performance
                        (XIRR/TWR), portfolio, holdings, dividends, diversity, market, etf_profiles (+ etf_presets.json), ...
    integrations/       external calls: currency (Frankfurter), yahoo_finance, notifications (ntfy, Telegram), logos, backup
    core/               cross-cutting: config, errors, security, logging, login_events, login_rate_limit, totp,
                        mcp_tokens, migrations, time, i18n (+ locales/{fr,en,es}.json: API texts according to Accept-Language)
    db/                 SQLAlchemy session, system_settings (get_setting/set_setting: set_setting only flushes, the service commits)
    models/             ORM models
    schemas/            Pydantic schemas
  data/                 dev SQLite
  scripts/              backup, backup_scheduler, restore, seed_demo, backfill
  tests/                backend pytest (~910 tests, ~1 min 45)
frontend/
  src/
    components/         layout, ui (shadcn), dashboard (+ tabs/), investments, settings, classement, import, audit, tools, analytics
    lib/                apiFetch, utils, countries
    types/              shared types (diversity.ts)
    pages/              main routes
    i18n/               i18next (fr/en/es), catalogues per domain, date and amount formats
    providers/          AuthProvider, UIProvider
mcp-server/             read-only MCP server (server.py + numera_mcp/ package: tools/<domain>.py, resources, prompts, api_client, auth)
infra/                  docker-compose.yml (dev), .prod.yml, .demo.yml, .images.yml (attached to releases)
Makefile, setup.sh, install.sh
```

## Backend layers

Layered architecture. Model domain: `accounts` (`controllers/comptes/accounts.py` → `services/comptes/accounts.py` → `repositories/comptes/accounts.py`). Phases 0 to 6 are done: the whole backend follows this model; the frontend is split (350-line cap respected everywhere, pages as `pages/<Page>/` folders) and its calls go through `lib/api/<domain>.ts` (one function per route on top of `lib/api.ts`). Figures are frozen by `tests/non_regression/test_analytics_snapshots.py` and `tests/non_regression/test_portfolio_snapshots.py`, the list of routes by `tests/garde_fous/test_openapi_routes.py`. The full OpenAPI schema is committed (`frontend/src/lib/api/generated/openapi.json`, checked by `tests/garde_fous/test_openapi_contract.py`) and is used to generate the frontend's TypeScript types (`make api-contract`, checked in CI).

`controllers/`, `services/` and `repositories/` are organised by domain, with the same tree in the three layers: `budget/`, `comptes/` (accounts), `investissement/` (investments), `analytics/`, `audit/` (services only; queries are in `repositories/analytics/audit.py`, the route in `controllers/analytics/audit.py`), `systeme/` (system; see the tree above). `controllers/deps.py` stays at the root. `domain/` and `integrations/` stay flat. A new module goes in the package of its domain, in each layer; a new router is added to `protected_routers` (`main.py`).

| Layer | Role | Does not import |
|---|---|---|
| `controllers/` | Controllers: HTTP, `Depends`, `Query`, one service call. No `db.query`, no `commit`, no import of `app.models`. | a `controllers.*` module of another domain (only `controllers.deps` and modules of its own domain package are allowed) |
| `services/` | Use cases: orchestration, **commit**, business errors (`NotFoundError` 404, `InvalidOperationError` 400, `BusinessRuleError` 422, `ConflictError` 409, `InternalError` 500, `ExternalServiceError` 502, `ExternalTimeoutError` 504 from `core/errors.py`, translated to HTTP by `main.py` with body `{"detail": …}`, or `{"detail": {"code", "detail", "context"}}` if a `code` is provided). | `app.controllers`, `fastapi` |
| `repositories/` | SQLAlchemy queries (`repositories/analytics/common.py`: `NET_AMOUNT`, `income_criterion`, `category_lines`…). Never `commit` (`flush` allowed). | `app.controllers`, `app.services`, `app.integrations`, `fastapi` |
| `domain/` | Pure calculations, no Session (`domain/transactions.py`: `net_amount`, `tx_sample`, `tx_read`; `budget`, `metrics`, `reports`, `insights`, `wrapped`, `projections`, `investments`, `budget_period`, `subscription_prices`, `tax`, `tax_rules`). | `app.controllers`, `app.services`, `app.repositories`, `app.integrations`, `app.db`, `sqlalchemy.orm`, `fastapi` |
| `integrations/` | External calls: `currency` (Frankfurter), `notifications` (ntfy/Telegram channels), `logos`, `backup`, `yahoo_finance` (search, prices, ETF composition). | `app.controllers`, `app.services`, `app.repositories` |
| `core/` | Cross-cutting only (config, security, logs, errors, rate limit, TOTP, MCP tokens, migrations, time); only imports `core`, `models` and `db`. | `app.controllers`, `app.services`, `app.repositories`, `app.domain`, `app.integrations`, `app.schemas` |

Value of an account: single source `services/comptes/wealth.py::account_values` (positions → statement → balance, exclusive `at` bound), reading statements and balances in batches through `repositories/comptes/balances.py` (`latest_snapshot`, `latest_transaction`, `latest_*_by_account`, `active_accounts`). The Accounts page, `/tax/overview`, the diversity scanner, the cash-flow projection, the month review and `/analytics/investments` use it; none copies the fallback rule.

Safeguards (ratchet, baselines only decrease): `backend/tests/garde_fous/test_architecture.py` + `architecture_baseline.txt` + `architecture_rules_baseline.txt` (the rules above, local imports included, imports of a missing `app.*` module, `commit()` outside `services/`, controllers with no import of `models|repositories|db|integrations|domain`, `core → fastapi`, `domain → models|schemas`, `integrations → models|db`, `starlette` in a service, `db.query/execute` in a service, `async def` without `await` outside controllers); `test_response_models.py` + `response_model_baseline.txt` (every endpoint has a 2xx or 204 response schema); `test_clock_guard.py` + `clock_baseline.txt` (no `datetime.now()`/`date.today()`/`utcnow()` outside `core/time.py`); `test_migrations.py` replays `upgrade head → downgrade → upgrade head` (floor `ece5365a3f43`, broken downgrade); `scripts/quality/check_code_size.py` + `scripts/quality/baselines/code_size_baseline.json` (caps of 400 lines per Python file, 80 per function, 350 per TS/TSX file outside `components/ui`), run by `make check-size` / `make validate` and by pytest. State (2026-11-05): sizes empty; the layer, response-contract and clock baselines are initialised on the existing code and protected by the CI "Cliquets" (ratchets) check.

## Backend

### Lifecycle

- `backend/app/main.py` creates the FastAPI application.
- On startup, `run_migrations()` runs Alembic except in the `test` environment.
- `seed_all()` inserts the default categories and the system ETF profiles except in `test`.
- A background task (`recurring_transactions_task`, every hour, first pass after 10 s) generates recurring transactions and pending salaries, refreshes prices and ETF compositions, then sends push notifications (`services/systeme/notifications.py` (channels: `integrations/notifications.py`)`::run_notifications`).
- `GET /health` and `POST /auth/token` are public.
- Demo mode (`DEMO_MODE=true`, package `services/systeme/demo/`: `guard`, `data`, `generator`): a dedicated database is mandatory (name containing "demo", checked by `config.py`). On startup and then on every pass of the background task, `ensure_demo_data` wipes the database and regenerates a deterministic fictitious 18-month dataset (4 accounts, linked transfers, a PEA with synthetic prices `security_prices.source = "demo"`, a life insurance by statements) if it is not from today. The background task then does nothing else (no real prices, no notifications); `get_market_quotes` serves the fictitious prices; the `demo_guard` middleware returns 403 on sensitive writes (`/admin/*`, TOTP, passkeys, notifications, logos, ETF refresh). Privacy and ceilings (audit M3/M4): the login journal records neither IP nor user-agent in demo; imports limited to 200 KB (413); 120 writes/min/IP (429, `demo_write_limiter`); backend container at 512 MB / 1 CPU. Deployment: `infra/docker-compose.demo.yml` (`make demo`, port 8090, public credentials demo / demo).
- The other routers are included with `Depends(get_current_user)`: session JWT, or MCP token (`core/mcp_tokens.py`: SHA-256 fingerprint in `mcp_tokens`, refused if revoked, if `mcp_enabled` is false or for any method other than `GET`/`HEAD`). The `/admin` router adds `require_interactive_session`: 403 for an MCP token.

### API modules

Files in `controllers/<domain>/` (see the tree); `/analytics/*` routes are in `controllers/analytics/`.

- `auth.py`: OAuth2 password login and JWT generation; `POST /auth/refresh` (sliding renewal of a valid session token, total duration capped by `SESSION_MAX_HOURS` through the `auth_time` claim, refused to MCP tokens); `GET /auth/whoami` (credential validation, used by the MCP server).
- `passkeys.py` (logic: `services/systeme/passkeys.py`): WebAuthn login (Face ID / Touch ID) in addition to the password. `GET /auth/passkey/available` (public), `POST /auth/passkey/login/{options,verify}` (public, same attempt limiter as the password), `GET/DELETE /auth/passkey` and `POST /auth/passkey/register/{options,verify}` (interactive session). Adding and deleting require re-authentication (body `current_password`, plus a TOTP or recovery `code` if 2FA is active: `register/options` only checks the password, the one-time code is checked at `register/verify` and on `DELETE`), through `services/systeme/admin.py::require_reauth`. Credentials as JSON in `system_settings` (`webauthn_credentials`), challenge in a signed 5-minute JWT; the `Origin` header must be in `CORS_ORIGINS` or have the request's host name (Host / X-Forwarded-Host); the RP ID is the host name.
- `totp.py` (logic: `services/systeme/totp.py`): TOTP two-factor authentication (RFC 6238, Google Authenticator), required **only after the password** (the passkey remains a sufficient factor). If active, `POST /auth/token` returns `{mfa_required, mfa_token, token_type: "mfa"}` (5-minute JWT `purpose=totp`, without `sub`, invalidated by a password change) instead of a session; `POST /auth/totp/login` (public, dedicated limiter) exchanges it with a code or a recovery code for the session. `GET /auth/totp/status`, `POST /auth/totp/{setup (password), enable (first code), disable (password + code), recovery-codes (code)}` (interactive session). Storage in `system_settings`: `totp_secret`, `totp_pending_secret`, `totp_last_step` (anti-replay), `totp_recovery_codes` (10 SHA-256 fingerprints, single use). Computation in `core/totp.py`, SVG QR code through `segno`.
- `accounts.py`: account CRUD, soft delete through `active=False` (logic in `services/comptes/accounts.py`, queries in `repositories/comptes/accounts.py`). Displayed balance: `services/comptes/accounts.py::account_balance` (last statement or last `running_balance` **dated today at the latest**, the more recent of the two); a `credit` account is worth −remaining principal.
- `loans.py`: loans (`/loans`). A loan = a `credit` account + a `loans` row, created and deleted together. Schedule, remaining principal and early-repayment simulation computed by `domain/loans.py` (`loan_remaining`: `services/comptes/loans.py`) (pure functions).
- `categories.py`: category CRUD with monthly/annual limits.
- `transactions.py`: transaction CRUD, merchant search, bulk update, grouped deletion (`POST /transactions/bulk-delete`, a single SQL transaction then one recomputation per account), balance recomputation.
- `investment_transactions.py`: operations `versement`, `retrait`, `achat`, `vente`, `dividende`, `frais` (logic in `services/investissement/investment_transactions.py`, queries in `repositories/investissement/investment_transactions.py`); every mutation calls `rebuild_holdings`. `POST /investment-transactions/link-dividends?account_id=&dry_run=` attaches old dividends with no security to a position based on their label.
- `balance_snapshots.py`: value snapshots and zero-point definition.
- `imports.py`: Numbers CSV preview/commit.
- `exports.py`: Numbers-compatible CSV export.
- `analytics/` (package, prefix `/analytics`): `metrics` (tags, expenses by category, top merchants, kpi-history, timeseries, calendar): calculations in the `services/analytics/metrics/` package (one module per route), queries `repositories/analytics/metrics.py`, formulas `domain/metrics.py`; `budget` (budget, budget-alerts, resilience: calculations in the `services/analytics/budget/` package (`summary`: steps of `compute_budget`, `alerts`, `resilience`), queries `repositories/analytics/budget.py`, formulas `domain/budget.py`); `investments` (investments, performance, allocations, net worth, simulation: package `services/analytics/investments/` (`summary`, `flows`, `account`, `allocation`, `projections`), queries `repositories/analytics/investments.py`, pure projections (FIRE, forecast, Monte Carlo) in `domain/projections.py`, breakdowns in `domain/investments.py`); `reports` (cashflow-projection, monthly-report, money-flow, sankey: package `services/analytics/reports/`, queries `repositories/analytics/reports.py`, formulas `domain/reports.py`); `subscriptions`, `insights` (calculations in `services/analytics/subscriptions.py` and `insights.py`); `audit` (audit + Action Center `/actions`, computed by `services/audit/`: `RULES` registry with one module per rule in `rules/`, data audit in `data_audit.py`); `diversity` (diversification scanner: `services/analytics/diversity.py`, ETF look-through, alerts and HHI score in `domain/diversity.py`); `dividends` (dividends in EUR: totals, per month / year / security, yields; `services/analytics/dividends.py`, pure aggregates in `domain/dividends.py`); `portfolio` (computed value, gains, XIRR/TWR, reconciliation; overview `services/analytics/portfolio.py::portfolio_overview`, also called by the net-worth forecast, and account by account `portfolio_account`); shared queries in `repositories/analytics/common.py` (including `income_criterion`, the single definition of income). Value of an account / net worth: `services/comptes/wealth.py`.
- `holdings.py`: security positions (`portfolio_holdings`, read-only apart from metadata; logic in `services/investissement/holdings/`: `inventory`, `enrich`, `replay`, `rebuild`, `cost_estimates`), Zero Point inventory (`POST /holdings/baseline` with optional `date`; `POST`/`PUT`/`DELETE /holdings` edit an inventory row), suggestions from notes. Each position carries `price_date` / `price_stale`.
- `market.py`: security search, validation and quotes (Yahoo Finance: `services/investissement/market/` + `integrations/yahoo_finance.py`, prices stored through `repositories/investissement/security_prices.py`).
- `etf_profiles.py`: ETF profiles (countries/sectors/top holdings; logic in `services/investissement/etf_profiles.py`, sources and reads in `domain/etf_profiles.py`). Composition fetched from Yahoo Finance (`quoteSummary`, `topHoldings` module: sectors + top 10, never countries): `POST /etf-profiles/auto-decompose` (creation), `POST /etf-profiles/{id}/refresh` (502 if Yahoo is unreachable), `POST /etf-profiles/refresh-held` (all held profiles). The background task refreshes held profiles at most once a week.
- `savings_goals.py`: savings goals computed by keyword.
- `categorization_rules.py`: local auto-categorisation rules based on the merchant.
- `recurring_transactions.py`: subscriptions and recurring transactions with automatic generation.
- `tags.py`: customisable cross-cutting tags.
- `salary.py`: salary configuration, remote-work (TT) days and generation of the associated transactions.
- `work_time.py`: net hourly rate = `net_salary × 12 ÷ (work_days_per_year × work_hours_per_day)` (218 days × 7 h by default), the basis of the price in working hours.
- `merchants.py`: management of canonical merchants and their normalisation aliases.
- `admin.py`: admin profile (name/password, `mcp_enabled`, `privacy_on_start` = open the app with amounts masked, key `ui.privacy_on_start`, stored in `system_settings`), login journal (`GET /admin/login-events?limit=`, table `login_events`), `POST /admin/logout-all` (pushes `auth_valid_after`: all sessions, including the current one, are refused; MCP tokens not affected), backup status (`GET /admin/backup/status`, `integrations/backup.py::backup_status`: `suivi_budget_*` files and `status.json` from `BACKUP_DIR`, `stale` beyond 2 days), MCP tokens (`GET`/`POST /admin/mcp-tokens`, `DELETE /admin/mcp-tokens/{id}`; the clear token is only returned at creation; creation requires `current_password`) and database reset (requires `current_password`, writes a snapshot `data/backups/pre-reset_*.db` before wiping).
- `notifications.py`: push-notification settings (`GET`/`PUT /notifications/settings`, tokens masked `••••` + last 4 characters; a token returned masked does not overwrite the value; changing `ntfy_server`, `ntfy_topic`, `ntfy_token`, `telegram_bot_token`, `telegram_chat_id`, `hide_amounts` or `public_url` requires `current_password` in the body, 400 otherwise) and `POST /notifications/test` (`channel` = `ntfy|telegram`, 400 if incomplete, 502 if sending fails). Forbidden to MCP tokens (`require_interactive_session`). Sending: `services/systeme/notifications.py` (channels: `integrations/notifications.py`).
- `health.py`: public healthcheck.

## Frontend

Routes in `frontend/src/App.tsx`:

- `/login`: authentication.
- `/`: dashboard, 5 tabs: Aperçu/Overview (`OverviewTab`), Budgets, Dépenses/Expenses (`MerchantsTab` + `SubscriptionsTab`), Analyse/Analysis (`InsightsTab` + `HistoryTab`), Projections. "All accounts" view by default, last chosen account remembered (`localStorage`).
- `/accounts`: account list (including the periodic validation banner). `?import=1` opens the CSV import (`components/import/ImportDialog`, no preselected account; ⌘K and the old `/settings?tab=import`).
- `/accounts/:id`: checking/savings/investment account detail; a `credit` account displays `components/loans/LoanView` (summary, remaining-principal curve, amortisation table by year, early-repayment simulator). `?new=tx&type=&amount=&merchant=` opens the pre-filled transaction form, `state.openTransaction` opens a transaction for editing (⌘K). "Importer" button: CSV import into this account (`ImportDialog` → `ImportFlow`).
- `/accounts?new=loan` opens the "Ajouter un crédit" (add a loan) form (`components/loans/LoanDialog`).
- `/savings`: savings goals.
- `/tax`: Taxation (card "Où placer ton prochain euro" — where to put your next euro, ceilings for PEA/PER/Livret A/LDDS/LEP/Livret Jeune, 5-year lock of the PEE, key PEA/life-insurance dates, yearly CTO recap 2DC/3VG/3VH).
- `/investments`: global investments view.
- `/month` (`MonthHub.tsx`, sub-routes): `/month/bilan` (monthly report, `MonthlyReport.tsx`), `/month/revue` (end-of-month review, `MonthReview.tsx`, `?year=&month=`), `/month/comparaison` (`Comparison.tsx`). Old addresses `/report`, `/month-review`, `/comparison` redirected with their parameters (`RedirectKeepingSearch`).
- `/recurring` "Échéances" (due dates): only one of the tabs `recurring` (List) or `subscriptions` (Recurrence analysis: Subscriptions / Investments / Other recurrences including salary, through `GET /analytics/subscriptions?include_other=true`) depending on the Analysis/List selector (localStorage `recurring-view`, default Analysis); then `?tab=` calendar (`Calendar.tsx` in `embedded` mode) | salary (`SalaryManager`, salary and remote work). `/calendar` redirects to `?tab=calendar`.
- `/audit`: Action Center (integrity audit, budget alerts, rule suggestions) — see `docs/ACTION_CENTER.md`. `?vue=virements`: internal-transfer review (`components/audit/TransferReview`: suggestions to link/ignore, linked transfers to unlink).
- `/classement` (Management group): `?tab=` tabs categories | tags | merchants | rules (auto-categorisation rules + transfer rules `TransferRulesSection`), components in `components/classement/`.
- `/tools` "Simulateur": simple forecast (`WealthForecast`, "in N years" + "what if I save +X") with an "Advanced mode" button to the full simulator (`WealthSimulator`).
- `/settings`: 4 `?tab=` tabs: general (profile, display: light/dark/auto theme specific to the device, amounts masked at opening, simplified positions; month splitting), notifications (ntfy/Telegram), security (password, passkey, TOTP, MCP access, recent logins + "log out all devices"), data (backup with its state, CSV export, import history, reset). Old tabs redirect: account → security, system → data, categories/tags/merchants/rules → `/classement`, transfers → `/audit?vue=virements`, import → `/accounts?import=1`.

Principles:

- `AuthProvider` manages the token and the login state.
- `ProtectedRoute` blocks application pages without a token.
- `UIProvider` carries the global UI state, including privacy mode.
- Omnibox (⌘K, `components/layout/Omnibox.tsx`): navigation, accounts, transaction search (direct opening for editing), actions (new transaction, CSV import, month review, privacy mode, add a loan) and quick entry `lib/quickEntry.ts` (`12,50 boulangerie` = expense, `+1200 prime` = income) which opens the pre-filled form on the main account, never a direct save.
- `apiFetch()` centralises JSON calls and redirects to `/login` on `401` (or `403` outside `/auth/token`). `API_BASE` = `http://localhost:8001` on localhost, `/api` elsewhere.
- CSV uploads do not use `apiFetch()` so the browser can set the multipart boundary; they go through `api.upload()`, which adds the Bearer without `Content-Type`. Exports use `api.download()`.

## Data model

### `accounts`

Main fields: `id`, `name`, `type`, `currency`, `created_at`, `active`, `color`, `asset_class`, `sector`, `geographic_zone`, `institution`, `logo` (ref `si:<slug>` or `file:<hash>.png`, same system as recurrences), `fonds_euros_pct`, `fonds_investis_pct` (life insurance), `is_main`, `last_verified_at`, `tax_wrapper` (`pea`, `per`, `cto`, `assurance_vie`, `livret_a`, `livret_jeune`, `pee`, `ldds`, `lep`, nullable) and `opened_at` (opening date) for the Taxation page. API deletion is soft (`active=False`).

Known types: `courant`, `epargne`, `investissement`, `assurance_vie` (`AccountType` in `schemas/account.py`, enforced on create/update), plus `credit`, created and modified only through `/loans`. A `credit` account has no transactions: its value is −remaining principal (`services/comptes/wealth.py`), 0 before disbursement (one month before the first instalment), so all net-worth totals are net; the KPI filters `type in (courant, epargne)` exclude it from income/expenses.

### `categories`

Fields: `id`, `name`, `icon`, `color`, `type`, `monthly_limit`, `annual_limit`, `group`, `archived` (hidden from selectors through `GET /categories?include_archived=false`, history and analytics unchanged).

`name` is unique. Limits feed the budget alerts.

### `transactions`

Fields: `id`, `account_id`, `date`, `month_label`, `type`, `merchant`, `merchant_id`, `category_id`, `amount`, `currency`, `original_amount`, `running_balance`, `note`, `is_recurring`, `recurring_transaction_id`, `is_subscription_ignored`, `custom_icon`, `custom_color`, `is_transfer`, `is_transfer_ignored`, `is_duplicate_ignored`, `linked_transaction_id`, `linked_investment_transaction_id`, `link_origin` (`manual` | `rule` | `recurring`), `transfer_rule_id`, `reimbursement_offset` (total reimbursed for a Sortie, total allocated for an Entree; maintained by `services/budget/reimbursements.py`). `is_exceptional` (out-of-the-ordinary expense: stays in totals and balances, isolated in the "excluding exceptional" read of the month review). `splits`: split parts (`transaction_splits`).

`amount` is the amount converted to the account currency. `original_amount` and `currency` keep the original entry. The link fields connect internal transfers or attach a transaction to the recurring rule that generated it.

### `investment_transactions`

Fields: `id`, `account_id`, `date`, `type`, `amount`, `currency`, `original_amount`, `note`, `asset_class`, `sector`, `geographic_zone`, `ticker`, `isin`, `quantity`, `unit_price`, `unit_price_derived`, `price_currency`, `fees`, `etf_profile_id`, `is_transfer`, `is_transfer_ignored`, `linked_transaction_id`, `link_origin`, `transfer_rule_id`, `recurring_transaction_id`.

Types: `versement` / `retrait` (cash flows, counted in the invested amount; with ticker + quantity they also move the position), `achat` / `vente` (security operations, ticker + quantity mandatory, no effect on the invested amount), `dividende`, `frais`. `unit_price` and `fees` are expressed in `price_currency` (default: `currency`); without `unit_price`, it is derived from the amount excluding fees (`unit_price_derived = true`) and recomputed on every change of amount, quantity or fees; an entered price is never overwritten. **Rule 12**: `InvestmentTransactionRead.is_upcoming` (computed field); position replay (`replay_account(until=end_of_today())`), cash and invested capital (`portfolio/cash.py`) ignore operations and transfer legs dated after today. The hourly task (`rebuild_due_holdings`) rebuilds the stored positions of accounts for which a security operation has just come due.

Valuation (`services/investissement/portfolio/`): for an `investissement` account that has positions, **value = Σ quantity × last price + cash**; cash starts from the Zero Point (statement − valued inventory, if a snapshot is within ±7 days) then accumulates `versement` +, `retrait` −, `achat` −, `vente` +, `frais` −, `dividende` + (a deposit/withdrawal carrying a security and a quantity is both an external flow and an operation: cash unchanged). Invested amount **since the account's origin**, independent of the positions' Zero Point date = (Zero Point snapshot if one exists) + all deposits − withdrawals dated after; with no Zero Point snapshot or deposit before the inventory, the opening value of the inventory counts as invested. Dividends do not increase it. The curve reuses the snapshots prior to the positions' Zero Point. Unrealised gain = value − EUR cost basis (rates at purchase), with `fx_effect_eur` = the share due to currency; realised gain replayed by `services/investissement/holdings/replay.py::replay_account` (net proceeds − EUR cost of the quantity sold, per year). XIRR (dated flows, current value last) and TWR (chain between flows, on the curve rebuilt with `security_prices` and dated rates). Snapshots become a check: a gap > 2 % on the last statement → action `reconciliation-gap-…`. Life insurance, an account without positions and an account with `accounts.valuation_mode = "snapshot"` (adjustable on the account page; crypto by default: names Coinbase/Ledger/… or rows only in `XXX-EUR` pairs) stay valued by snapshot (`value_source`). `/analytics/investments`, `/investments/{id}` and `/performance-history` use this value for securities accounts.

Dividends (`services/investissement/dividends.py` + `domain/dividends.py`): `ticker` mandatory at creation, `amount` = **net received** (as at the broker), `withholding_tax` = informational withholding (same currency as `currency`, gross = net + withholding), `reinvested` = a linked `achat` (`reinvest_of_id`, not editable by hand) is generated with `quantity` = shares received. An entered dividend marks the position as distributing (`portfolio_holdings.pays_dividends`, adjustable by hand).

### `balance_snapshots`

Fields: `id`, `account_id`, `date`, `current_value`, `note`, `is_zero_point`.

A zero point serves as the performance baseline for an account.

### Other tables

- `portfolio_holdings`: security positions per account (`account_id`, `ticker`, `isin`, `asset_name`, `quantity`, `buy_price_avg` = average cost (PRU) fees included in `currency`, `cost_basis_eur` = cost at historical rates, `pays_dividends` = distributing security (reminder), `etf_profile_id`). **Derived**: recomputed by `services/investissement/holdings/rebuild.py::rebuild_holdings` = `holding_baseline_items` inventory + security operations after `accounts.holdings_baseline_date` (a security operation before it is refused with 422).
- `holding_baseline_items`: Zero Point inventory of positions (`account_id`, `baseline_date`, `ticker`, `quantity`, `buy_price_avg`, `currency`, `cost_basis_eur` = entered EUR cost basis, taking priority over converting `buy_price_avg` at the Zero Point rate; without it, a foreign-currency security is flagged in the tax recap (`/tax/annual-report`, `warnings`). Re-saving the inventory without this field keeps the entered value, `null` clears it).
- `security_prices`: daily closing prices (`ticker`, `date`, `close`, `currency`, `source`), fed on every Yahoo quote (`get_market_quotes(..., db=)`), by the hourly background task (`refresh_held_prices`) and by `get_price_on` / `fetch_price_history`. If Yahoo fails, the last stored price is returned with `stale=True`.
- `etf_profiles`: ETF profiles (`name`, `ticker`, `isin`, `aliases`, `countries`, `sectors`, `top_holdings` as JSON text, `is_system`, `composition_sources`, `composition_refreshed_at`). `composition_sources` gives the source of each field: `yahoo` (rewritten on every refresh), `preset` (preset of the system profiles in `domain/etf_presets.json`, fallback while Yahoo does not provide the field, rewritten at startup), `manual` (entered through `PUT`, never overwritten). The diversity scanner counts the uncovered share of an ETF as "Non renseigné" (not provided) and returns the origin of compositions in `etf_compositions`.
- `system_settings`: key/value pairs (e.g. `admin_username`, `admin_password_hash`, `mcp_enabled`, `ui.privacy_on_start`).
- `login_events`: login attempts (`created_at`, `method` = `password|password_totp|passkey`, `success`, `reason` = `invalid_password|invalid_totp|invalid_passkey|rate_limited`, `ip` (Nginx X-Real-IP), `user_agent`). Written by `core/login_events.py::record_login` from `/auth/token`, `/auth/totp/login`, `/auth/passkey/login/verify`; only the last 200 are kept.
- `mcp_tokens`: MCP access tokens (`name`, unique SHA-256 `token_hash`, `token_prefix` for display, `created_at`, `last_used_at`).
- `imports_log`: CSV import journal.
- `historical_exchange_rates`: historical-rate cache, unique per `(date, currency)`; written by `services/comptes/exchange_rates.py` (`INSERT … ON CONFLICT DO NOTHING` through `repositories/comptes/exchange_rates.py`), never committing the caller's session.
- `savings_goals`: savings goals (`name`, `target_amount`, `keyword`, `deadline`, `account_id`, `category_id`, `icon`, `color`).
- `categorization_rules`: local auto-categorisation rules based on merchant patterns (`id`, `pattern`, `category_id`, `transaction_type`, `merchant_name`, `priority`). `merchant_name` attaches `transactions.merchant_id` to a canonical merchant (created if needed): the bank label `merchant` is never modified (rule 7). `apply-all` leaves split expenses their type.
- `recurring_transactions`: definitions of recurring subscriptions/fixed charges (`id`, `account_id`, `name`, `type`, `amount`, `currency`, `category_id`, `frequency`, `day_of_month`, `start_date`, `end_date`, `excluded_months`, `last_generated_date`, `is_active`, `auto_generate`, `note`, `transfer_to_account_id`, `transfer_credit_day`, `asset_class`, `sector`, `geographic_zone`, `ticker`, `isin`, `quantity`, `unit_price`, `whole_shares`, `etf_profile_id`).
- `transfer_rules`: internal-transfer rules (`source_account_id`, `dest_account_id`, `pattern` on the outflow's merchant/note, `amount`, `amount_tolerance_pct`, `day_tolerance`, `is_active`). Engine: `services/budget/transfers.py`.
- `reimbursement_claims` (claim: `transaction_id` → Sortie, `debtor`, `expected_amount`, `note`) and `reimbursement_allocations` (`claim_id`, `entree_transaction_id`, `amount`, unique per pair). Engine: `services/budget/reimbursements.py`; KPIs use `NET_AMOUNT = amount − reimbursement_offset` (`repositories/analytics/common.py`).
- `month_closures` (end-of-month review: `year` + `month` unique together, `closed_at`, `highlight`, snapshot `tx_count` / `income` / `expenses` / `unresolved_count`, plus `fingerprint`: inflow/outflow totals per account currency as JSON, without conversion). Non-blocking marker; "modified since closing" = `tx_count` or `fingerprint` different from the recomputation (exact comparison, insensitive to exchange rates). Logic: `services/budget/month_review.py`, route: `controllers/budget/month_review.py`.
- `tags`: custom cross-cutting tags (`id`, `name`, `color`, `archived`).
- `transaction_splits`: split of a non-transfer `Sortie` across categories (`transaction_id` CASCADE, `category_id`, `amount`, `note`); sum of parts = amount, no Investissement/Epargne part nor `revenu` category, the transaction takes the category of the largest part. Logic: `services/budget/splits.py`. Only the breakdowns by category read the parts, through `repositories/analytics/common.py::category_lines` (`expenses-by-category`, `budget-alerts`, `sankey`, variable `money-flow`, provisions, the `category_id` filter of `/transactions`); totals, balances and real expenses unchanged. Changing the type/amount of a split transaction → 400; changing its category, bulk re-categorising it or linking it as a transfer cancels the split.
- `loans`: loan parameters (unique `account_id` CASCADE to a `credit` account, `kind` = `immobilier|auto|consommation|etudiant|autre`, `principal`, `annual_rate_pct`, `duration_months`, `start_date` = date of the 1st instalment, `insurance_monthly`). Constant instalment excluding insurance, instalment n at `start_date + (n−1) months`, rounded to the cent per row, the last row settling the remainder.
- `loan_prepayments`: early repayments made (`loan_id` CASCADE, `date`, `amount`, `mode` = `reduce_duration` keeps the instalment, `reduce_payment` recomputes it over the remaining duration), applied after the last instalment dated ≤ `date`.
- `financial_events`: decision journal (`date`, `title` ≤ 200, `note` ≤ 1000, optional `account_id` SET NULL). A context note with no effect on calculations, displayed as a ⚑ marker (in its calendar month) with the highlights of closures on the "Flux de trésorerie" (cash flow) curve of the Dashboard History tab, and managed by the `components/dashboard/DecisionJournal` card.
- `provisions`: large periodic expenses (`name`, `amount` EUR per due date, `interval_months`, `due_date` = reference due date, `category_id` to find the actual payment, `account_id` = set-aside account, `note`, `active`). Purely forward-looking, no transaction created. Calculation `services/budget/provisions.py`: next/previous due date, `target_now` = amount × time elapsed since the previous due date, `monthly_needed` = (amount − accumulated) ÷ remaining months; accumulation = balance of the linked account (`services/comptes/wealth.py::account_values`) split among its provisions in proportion to their target; `behind` if accumulated < target − €1; `last_payment` = largest expense of the category within ±60 days of the previous due date.
- `benefits`: benefits received every month (`name`, `organization`, `amount` = expected monthly amount, `payment_day`, `match_pattern` = text searched in the label or note of inflows, `account_id` = optional receiving account (SET NULL), `start_date`, `declaration_interval_months` + `next_declaration_date` = periodic declaration, quarterly for the activity bonus, `logo` = `si:<slug>` / `file:<hash>.png` like recurrences, `auto_generate` = monthly entry (requires `account_id`), `note`, `active`). Benefits stay ordinary income in KPIs. Generation (`services/budget/benefit_generation.py`, hourly task, "benefits" steps): when the payment day is reached, a provisional `Entree` (`transactions.is_provisional`, `transactions.benefit_id` → logo through `recurring_logo`) at the expected amount is created on the receiving account, unless the real payment is already there or a generated entry exists for the month (idempotent, current month only). `reconcile_provisional` (CSV import + task) replaces each provisional entry with the real inflow whose label contains the pattern (same account, ±10 days, 1-to-1 matching on the closest amount), which inherits the `benefit_id`, then recomputes balances. Provisional entries do not count as a received payment. Calculation `services/budget/benefits.py` (pure parts: `domain/benefits.py`): payments = non-transfer inflows containing the pattern (last 400 days); an inflow matching several benefits goes to the one whose expected amount is closest; month status `received` (payment since expected − 10 days) / `late` (nothing 5 days after the expected date) / `pending`; `amount_changed` if the last payment differs by more than €1 and 5 %. Action Center (`services/audit/rules/benefits.py`): `benefit-declaration-{id}-{date}` (7 days before, `high` when late), `benefit-late-{id}-{YYYY-MM}`, `benefit-amount-{id}-{date}`.
- `notification_log`: alerts already notified (unique SHA-256 `fingerprint` of the `ActionItem`'s `id|title|description`, `action_id`, `channel` = channels that received or `init`, `sent_at`). Settings in `system_settings` (`notify.*`: channels, minimum severity, weekly digest, amount masking, public URL, `notify.initialized`, `notify.last_digest_week`).
- `transaction_tags`: many-to-many association table (`transaction_id`, `tag_id`).
- `merchants`: canonical merchants (`id`, `name`, `category_id`, `icon`, `color`).
- `merchant_aliases`: aliases and original bank labels associated with canonical merchants (`id`, `merchant_id`, `label`).
- `salary_configs`: salary configuration for TR/TT generation (`id`, `salary_account_id`, `ticket_account_id`, `net_salary`, `ticket_value`, `ticket_employee_share`, `salary_category_id`, `ticket_category_id`, `salary_recurring_id`, `ticket_recurring_id`, `is_active`).
- `salary_months`: salary generation status per month (`id`, `salary_config_id`, `month_label`, `salary_date`, `ticket_date`, `is_generated`, `generated_at`).
- `telecommuting_days`: remote-work days declared per month (`id`, `salary_config_id`, `date`, `month_label`).
- `dismissed_insights`: spending insights/anomalies hidden by the user (`id`, `title`, `dismissed_at`; `title` stores the stable `id` of a hidden insight/action).

## Main routes

### Public

- `GET /health` → `{"status": "ok", "demo": bool}` (the frontend displays the demo credentials and a banner when `demo` is true)
- `POST /auth/token` (attempt limit per client/user)
- `GET /auth/whoami` (authenticated: JWT or MCP token)

### CRUD and data

- `/accounts` (+ `POST /{id}/verify`; `POST /{id}/reconcile` `{date, bank_balance}`: reconciliation with the balance displayed by the bank, read-only. Compares with the end-of-day `running_balance` and lists leads (`duplicate`: same label, direction and amount within ≤ 3 days; `extra_or_missing`: a row whose amount equals the gap; `wrong_sign`: a row whose inversion closes the gap; `missing` as a fallback), searched over the 60 days before the date. Gap ≤ 0.01 → `last_verified_at` updated. Logic: `services/comptes/reconciliation.py`. UI: "Rapprocher" button of `AccountDetail` and "Saisir le solde" of the verification banner, `components/accounts/ReconcileDialog`)
- `/categories`
- `/transactions`
- `/investment-transactions`
- `/balance-snapshots`
- `/goals`
- `/provisions`: `GET` (list with computed state), `GET /summary` (monthly total, due dates within 90 days, gap per linked account), `POST`, `PATCH /{id}`, `DELETE /{id}`
- `/benefits`: `GET` (list with computed payments and status), `GET /summary` (expected monthly, received in the year and over 12 months, benefits not received, next declaration), `POST`, `PATCH /{id}`, `POST /{id}/declared` (declaration done: due date moved forward by one interval, optional `amount` = new amount), `DELETE /{id}`
- `/loans`: `GET` (summaries: current instalment, remaining principal, % repaid, end date, total cost), `POST` (creates the `credit` account and the loan), `GET|PATCH|DELETE /{id}` (deletion also removes the account), `GET /by-account/{account_id}`, `GET /{id}/schedule`, `POST /{id}/simulate-prepayment` (`amount`, `date`, `mode`; nothing is saved; `max_penalty` = legal cap min(6 months of interest, 3 % of remaining principal)), `POST /{id}/prepayments`, `DELETE /{id}/prepayments/{pp_id}`
- `/financial-events`: decision journal, `GET` (optional `start`, `end`, `account_id`, most recent first), `POST`, `PATCH /{id}`, `DELETE /{id}`
- `/categorization-rules`
- `/recurring-transactions` (+ `POST /trigger`); `transfer_to_account_id` makes it a "transfer" recurrence (linked outflow + inflow at each due date); `transfer_credit_day` (1-31, optional) delays the arrival: the outflow carries `transactions.transfer_credit_due` (first day `transfer_credit_day` from the debit) and the inflow is only created at that date by the background task (never if the outflow was linked or unlinked in the meantime); `whole_shares` (buying securities without a fixed quantity): quantity rounded down to the integer and deposit amount = shares × price (the remainder stays at the broker, the bank outflow keeps the planned amount); optional `logo` (`si:<slug>` Simple Icons or `file:<hash>.png` local favicon), reused by `TransactionRead.recurring_logo` and by the events of `/analytics/calendar` (`logo`); on read, `security_name` (computed, not stored) gives the readable security name: linked ETF profile (`etf_profile_id`), otherwise ETF profile of the same ticker, otherwise `asset_name` of the held position (3 grouped queries, `repositories/budget/recurring.py::security_name_sources`)
- `/logos`: `GET /search?q=` (embedded Simple Icons catalogue `app/assets/simple_icons/`, CC0), `POST /from-domain` (downloads a domain's favicon once through Google's favicon service, stored in `data/logos/`, setting `logos_dir`); `GET /logos/img/{ref}` is **public** (read-only, reference validated by regex) because an `<img>` tag does not send the JWT
- `/transfer-rules` (CRUD, `PATCH /{id}` to edit a rule from Settings › Transfers, `POST /apply[?dry_run=true&rule_id=]`: catch-up of the history)
- `/reimbursements`: `GET /claims?status=open|settled|all&debtor=`, `GET /summary`, `POST /claims`, `PATCH|DELETE /claims/{id}`, `GET /claims/{id}/candidates`, `POST /claims/{id}/allocations`, `DELETE /allocations/{id}`, `GET /entries/{entree_id}/claims`
- `/month-review`: `GET ?year=&month=` (steps categorise, balances, budget + closing status + `modified_since_close`), `POST /close` (`year`, `month`, `highlight`, idempotent), `DELETE ?year=&month=` (reopen, 204), `GET /closures`
- `/transactions/potential-transfers[?months=&days_tolerance=&amount_tolerance_pct=]` (suggestions; by default the whole history, ±5 days, ±1 %), `GET /transactions/{id}/transfer-candidates` (manual linking), `POST /transactions/{id}/transfer-counterpart`, `link/{other_id}`, `unlink`, `ignore[?other_id=]`
- `/tags` (`GET ?include_archived=false` hides archived ones)
- `PUT /transactions/{id}/splits` (`{items:[{category_id, amount, note}]}`, empty list = cancel); `GET /transactions` also accepts `uncategorized`, `merchant_name` (exact canonical name), `period=true` (month/year = pay month) and `budget_scope=true` (checking/savings excluding meal vouchers): filters of the charts' drill-down panel
- `/merchants` (+ aliases, `auto-normalize`, `suggestions/unnormalized`)
- `/holdings`, `/etf-profiles`, `/market` (search, validate, quote)
- `/tax` (`GET /tax/overview`, `GET`/`PATCH /tax/settings`, `GET /tax/annual-report?year=`): calculations in `services/investissement/tax.py`, figures per year in `domain/tax_rules.py` (values to verify), pure calculations in `domain/tax.py`; `overview.suggestions` = active accounts without a wrapper whose name suggests one (`domain/tax.py::guess_tax_wrapper`), proposed on the page without saving anything by default; `overview.allocation_advice` = recommended filling order (`domain/tax.py::allocation_advice`, fixed rule: emergency savings < 6 months of expenses (`compute_resilience`) → first savings account with room among LEP, Livret A, LDDS, Livret Jeune; PEA with room or to open; PER if marginal tax bracket ≥ 30 %; life insurance to open otherwise CTO), `overview.precaution_months`; LDDS ceiling €12,000 and LEP €10,000 (reminder of the income condition, not verified)
- `/salary` (config, months, telecommuting, summary, generate, work-time: net hourly rate for the price in working hours, settings `work_days_per_year` / `work_hours_per_day` in `system_settings`)
- `/admin` (profile, mcp-tokens, reset-database) — forbidden to MCP tokens

### Import / export

- `POST /import/preview`
- `POST /import/commit`
- `GET /export/transactions.csv`

### Analytics

- `GET /analytics/budget` (global view: `epargne_realisee` = income − real expenses, numerator of the savings rate; `reste_tresorerie` = `epargne_realisee` − `investissements_du_mois` (linked deposits included); `revenus_apres_depenses` remains income − `depenses_totales`)
- `GET /analytics/actions`, `POST /analytics/actions/dismiss`, `GET /analytics/audit`, `GET /analytics/audit/{issue_id}`
- `GET /analytics/cashflow-projection` (today's balance + `recurring` events (projected due dates, never stored) and `scheduled` (entered upcoming transactions, with `transaction_id`); a due date already entered under the same `recurring_transaction_id` is not counted twice, and an entry close to a due date of the same direction and amount (≤ 3 days) is flagged `possible_duplicate` (`domain/reports.py::flag_possible_duplicates`), without merging; global view: ignores transfer recurrences to an account already counted in the balance and "lapsed" recurrences; account view: a "transfer" recurrence whose `transfer_to_account_id` is this account is projected there as an inflow, in the account currency, at the arrival date `transfer_credit_date`). `GET /analytics/calendar` applies the same rules (inflow projected on the destination account in account view, transfer between two counted accounts ignored in global view). Feeds the "À venir" (upcoming) card of `AccountDetail` (`UpcomingCard`, 30-day horizon), `GET /analytics/calendar` (each event carries `is_upcoming`; `TransactionRead.is_upcoming` for lists), `GET /analytics/patrimoine-allocation` (loans outside the items: `total_debts_eur`, `net_patrimoine_eur`)
- `GET /analytics/asset-allocation/suggestions`, `GET /analytics/diversity-scanner`
- `POST /analytics/insights/dismiss` (body `{key}`: stable key `Insight.key` = kind + month + object, e.g. `large-expense-{tx_id}`, `subs-increase-2026-10`; stored in `dismissed_insights.title`), `GET /analytics/subscriptions` (`kind` per row, `totals_by_kind`, `in_kind_total`), `POST /analytics/subscriptions/ignore`, `GET /analytics/tags`
- `GET /analytics/expenses-by-category`
- `GET /analytics/top-merchants`
- `GET /analytics/investments`
- `GET /holdings/estimate-costs?account_id=`: estimated average cost (PRU) of each Zero Point row from purchases prior to its date (+ `coverage`); `POST /holdings/apply-costs` saves the validated PRUs
- `GET /analytics/dividends` (`account_id`, `months`)
- `GET /analytics/portfolio` (global EUR view) and `GET /analytics/portfolio/{account_id}`: computed value, cash, invested amount, unrealised gain (+ currency effect per line), realised gain per year, dividends, fees, XIRR, TWR, rebuilt curve, reconciliation with snapshots
- `GET /analytics/investments/{account_id}`
- `GET /analytics/investments/{account_id}/performance-history`
- `GET /analytics/subscriptions` (`price_changes`: recent price increases, `services/budget/subscription_prices.py`, series: `domain/subscription_prices.py`; a series = outflows of the same account attached to the same recurrence, otherwise to the same canonical merchant, otherwise to the same label, with a regular due date (median gap monthly 25-35 days, quarterly 80-100 days, yearly 340-390 days) and still being debited; increase = latest run of identical amounts at least 0.10 and 1 % above the previous stable run (two due dates, one for yearly), flagged for 6 months (13 for yearly); picked up in the Action Center as `subscription-price-{account}-{key}-{date}`) (`status`: `active`, `lapsed` = active but no occurrence for more than two periods + 7 days (`domain/finance.py::is_lapsed`, excluded from totals), `paused`, `potential`; `next_occurrence` searched over 400 days)
- `GET /analytics/wrapped?year=` (yearly review, `services/analytics/wrapped.py` (formulas `domain/wrapped.py`): aggregates month by month `budget`, `expenses-by-category` (excluding Investissement/Epargne) and `top-merchants`; current year stopped at the current month, `previous` = N-1 over the same period, only if N-1 has expenses in at least half of the compared months; net worth change excluding opening balances entered in the year; subscriptions = `Sortie` recurrences excluding transfers and savings/investment, new = 1st due date in the year, stopped = ended recurrence (or "lapsed" at the end of the period) whose last due date falls in the year; working hours at the current hourly rate)
- `GET /analytics/kpi-history` (same rules as `budget`: internal transfers excluded, only deposits linked to a transfer count as invested; `taux_epargne` capped at ±100, `null` without income; `depenses` includes outflows categorised Investissement/Epargne, `depenses_reelles` does not)
- `GET /analytics/budget-period[?year=&month=]` and `PUT` (`{"mode": "civil"|"salary"}`): current budget month and window (`start`, `end` inclusive) of the requested month. Pay month (setting `budget_month_mode`, default `salary`): each salary received (an `Entree` transaction of the salary account whose label starts with "Salaire", or from a salary recurrence, or of category "Salaire") opens a period that lasts until the next salary and bears the name of the month it finances (salary of 25 August → "September"). Single logic in `services/budget/budget_period.py` (`period_bounds`, `period_key_expr`, `current_period`; period computation in `domain/budget_period.py`, salary dates in `repositories/budget/budget_period.py`); wired into `budget`, `budget-alerts`, `expenses-by-category`, `top-merchants`, `tags`, `kpi-history`, `timeseries`, `monthly-report`, `money-flow`, `sankey`, `insights`, `/month-review`. Without a detected salary: calendar month. Missing salary (gap > 45 days): the hole between two periods forms a "no salary" month (`_fill_gaps`), no day is outside a period. Out of scope (stay calendar month): balances, calendar, cashflow-projection, investments, taxation, `/wrapped` (forced to calendar by `civil_months()`)
- `GET /analytics/resilience?month=&year=` (months of autonomy = liquid savings ÷ average real expenses of the last 6 complete months; also used by the "safety fund" of the health score)
- `GET /analytics/account-flow-summary` (net flow of the month, change, average spend of an account; transfers excluded)
- `GET /analytics/investments-allocation`
- `GET /analytics/investments-allocation-advanced` (breakdown of what is held: value of each position classified like its security, cash under "Liquidités"; account without positions: purchases net of sales per security)
- `GET /analytics/timeseries`
- `GET /analytics/budget-alerts`
- `GET /analytics/insights`
- `GET /analytics/wealth-simulation` (advanced mode: Monte Carlo, events, taxation)
- `GET /analytics/wealth-forecast` (simple forecast: total net worth + 12-month average savings (excluding leading months with no spending, before the start of tracking), observed XIRR (`/analytics/portfolio`) applied only to accounts valued by positions on which it is measured (`investissement`), investment accounts tracked by statement at 0 % (`investissement_non_mesure`) except `investment_return_pct` which applies to all, other accounts 0 %, no hard-coded rate, `years`, `extra_monthly`, overrides `monthly_savings` / `investment_return_pct` / `savings_return_pct`; the response details the months and balances per type used)
- `GET /analytics/fire` (financial independence: target = annual expenses ÷ `withdrawal_rate_pct` (4 by default), average real expenses and savings of the `wealth-forecast` months, nominal return of `wealth-forecast` minus `inflation_pct` (2 by default) → projection in constant euros, `years_to_fi` (`null` beyond 80 years), scenarios +100/+250/+500 €/month and expenses −10 %; overrides `return_pct`, `monthly_savings`, `annual_expenses`)
- `GET /analytics/sankey` (expense category nodes carry `category_id`, clickable to the drill-down panel; balanced Budget node: Investissements = `investissements_du_mois`, Épargne = inflows − categorised expenses − investments, Déficit otherwise)
- `GET /analytics/money-flow` (global view: `investments` includes deposits linked to an internal transfer, like `investissements_du_mois`)
- `GET /analytics/monthly-report` (`net_worth_change` excluding opening balances entered in the month; includes `exceptional_expenses`, `real_expenses_excl_exceptional`, `savings_excl_exceptional`, `savings_rate_excl_exceptional`, `burn_rate_excl_exceptional`; `top_categories`: first 8 categories with `prev_total`, total of the previous month)

## Calculation rules

- `Entree` and `Interets` increase the balance.
- `Sortie` decreases the balance.
- `Solde Initial` replaces the current balance with the starting amount.
- For a filtered period, `Solde Initial` is excluded from income.
- Real expenses exclude internal transfers to `Investissement` and `Epargne` when the calculation requires it.
- The savings rate uses real expenses and is capped between `-100` and `100`.
- The burn rate is computed over the elapsed days of the current month or the number of days of a past month.
- Investments use snapshots for the current value and operations for the flows.

## CSV import

Pipeline:

1. UTF-8 reading, BOM tolerated.
2. Delimiter detection `,`, `;` or tab.
3. Header normalisation with `HEADER_ALIASES`.
4. Validation of mandatory columns: `Date`, `Mois`, `Type`, `Commercant`, `Categorie`, `Montant` (French header names, as exported by Numbers).
5. Parsing of French/English dates and amounts.
6. Type normalisation via `normalize_transaction_type()`.
7. Manual category mapping, optional creation of missing categories.
8. Duplicate detection: key `(date, amount, merchant, type)` on the file's raw values (before rules), compared with `transactions.original_merchant` / `original_type` (falling back to `merchant` / `type`).
9. Insertion with running balance, `imports_log` journal, then `recalculate_running_balances` if at least one row is imported.

## Multi-currency

- Current rates: Frankfurter, 6-hour memory cache.
- Historical rates: Frankfurter, SQLite cache in `historical_exchange_rates`.
- Offline EUR fallback: `EUR=1.0`, `USD=1.08`, `GBP=0.84`, `CHF=0.95`.
- Conversion to EUR: `amount / rate` when `rate` represents `1 EUR = X currency`.

## Backups

- The Docker service `backup` runs `backend/scripts/backup_scheduler.py`.
- Source: `backend/data/suivi_budget.db` mounted in `/app/data`.
- Destination: `backups/` at the root through `/app/backups`.
- Variables: `BACKUP_KEY`, `BACKUP_INTERVAL_SECONDS`, `RETENTION_DAYS`, `GITHUB_BACKUP_KEEP_DAYS` (read from `.env` and passed on by the three compose files).
- Before a migration that changes the schema, `core/migrations.py` copies the database to `BACKUP_DIR/pre_migration_<rev>_<date>.db[.enc]` (5 kept).
- Commands: `make backup-now`, `make backup-restore FILE=...`.
- Docker update: `install.sh --upgrade` (or `NUMERA_UPGRADE=1`; the published compose pins the version; `SHA256SUMS` checksum attached to the release).

The `BACKUP_KEY` key is essential to restore encrypted backups.
