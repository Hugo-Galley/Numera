---
name: numera-clean-architecture
description: Use when deciding where new Numera code goes (controller, service, repository, domain, integration, frontend), when moving or splitting a file, when a calculation might already exist elsewhere, or when test_architecture.py / check_code_size.py fails.
---

# Numera — clean architecture

## Principle

One responsibility per layer, one definition per business rule. The safeguards (`tests/garde_fous/test_architecture.py`, `scripts/quality/check_code_size.py`) catch imports and sizes; this skill covers what they do not see. Detailed import rules: `backend/CLAUDE.md` § Layers.

## Where does this code go?

| The code… | Layer | Forbidden |
|---|---|---|
| reads the HTTP request, chooses the 401/403/413/429 error code | `controllers/<domain>/` — one line that calls a service | logic, SQL query, `commit` |
| orchestrates a use case, `commit`, raises a business error | `services/<domain>/` | `fastapi`, `HTTPException`, importing a controller |
| queries the database | `repositories/<domain>/` | `commit`, calling a service |
| computes (amount, date, aggregate, ranking) with no I/O | `domain/` | `Session`, `sqlalchemy.orm`, network |
| talks to the network (Yahoo, Frankfurter, ntfy) | `integrations/` | business logic |
| displays | `frontend/src/` | any KPI, total, ratio, computed status |

A calculation in a service that can only be tested with a database → extract it into `domain/` and test it in memory (`numera-tdd`).

## A single definition (source of truth)

Audits A1–A12 almost all came from the **same rule coded twice** that then diverged. Before writing a calculation, look for what exists:

```bash
grep -rn "def .*<keyword>" backend/app/domain backend/app/services backend/app/repositories
```

| Notion | Single source |
|---|---|
| Income | `repositories/analytics/common.py::income_criterion` |
| Account value / net worth / displayed balance | `services/comptes/wealth.py::account_values` (Accounts page, taxation, diversity, cash flow, investments: never a copied fallback) |
| Last statement / last transaction of an account, active accounts | `repositories/comptes/balances.py` (`latest_snapshot`, `latest_transaction`, batch versions `latest_*_by_account`; exclusive `before`) |
| Active recurrences | `repositories/analytics/common.py::active_recurrings` |
| Running balances | `services/budget/balances.py::recalculate_running_balances` |
| Security positions | `services/investissement/holdings/rebuild.py::rebuild_holdings` |
| Portfolio valuation | `services/investissement/portfolio/compute.py::compute_portfolio` (short cache: `portfolio/cache.py`) |
| Budget | `services/analytics/budget/summary.py::compute_budget` (call the service, never a route function) |
| Salary | `domain/salary.py::salary_amount` |
| Amount format (front) | `lib/utils.ts::formatCurrency` |

Need a variant? Parameterise the existing function, do not copy it. A new cross-cutting notion → add it to this table.

## Moving or splitting code

1. Tests green before starting; the move changes no test except its imports.
2. Update **all** importers: absolute, relative, local imports inside functions, `monkeypatch.setattr("old.module…")`, scripts (`scripts/`, `backend/scripts/`, `Makefile`, `docker-compose*.yml`, `infra/`).
3. No re-export from the old location; delete the old file.
4. Check non-Python paths: `grep -rn "old/path\|old\.module" --exclude-dir=node_modules .` (the "demo" and "backup" fixes came from a move forgotten in `Makefile`/script).
5. A domain does not import another domain's controller: go through the service.

## Ratchets (baselines)

`scripts/quality/baselines/code_size_baseline.json` (import rules no longer have a baseline: zero violations) only **decreases**. A new violation is fixed in the code (split, move), never by regenerating the baseline. Regenerating is only allowed to remove an entry that disappeared or to rename a key during an identical move.

## Rationalisations

| Excuse | Reality |
|---|---|
| "Just a small calculation in the router" | The router becomes untestable and the calculation will be copied elsewhere. Service or `domain/`. |
| "I compute the total on the front side, it's display" | A total is a KPI. Backend (critical rule no. 2). |
| "I duplicate so as not to break the existing" | Duplication *is* the future bug. Parameterise, with tests. |
| "I re-export for compatibility" | Forbidden. Update the importers. |
| "I add the line to the baseline, I'll split later" | Later never comes. Split now. |
| "`HTTPException` in the service, it's more direct" | Errors from `core/errors.py`; the handler translates them. |

## Stop signals

`fastapi` import outside `controllers/` · `db.commit()` in a repository · arithmetic on amounts in a `.tsx` · two functions that compute the same notion · a regenerated `*baseline*` file · an old module left "just in case".
