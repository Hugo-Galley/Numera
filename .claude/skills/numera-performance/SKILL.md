---
name: numera-performance
description: Use when optimizing or reviewing performance in Numera — a slow route or page, a new endpoint that loops over rows, a new cache, an index question, a bundle or nginx change — and before writing any code that loads many rows, calls the database inside a loop, or caches a result.
---

# Numera — performance

## Principle

**Measure, fix the cause, prove the gain.** An optimisation without a before/after figure is an opinion. The real database is small (≈ 200 transactions): everything is instantaneous there, so problems only show on a large dataset. Test procedure: `numera-tdd`; where the code goes: `numera-clean-architecture`; validation: `numera-finishing`.

## 1. Measure first

```bash
cd backend && export PYTHONPATH=.
python3.11 scripts/perf_profile.py seed --db /tmp/perf_demo.db --months 240 --multiply 6   # ≈ 50,000 transactions
python3.11 scripts/perf_profile.py bench --db /tmp/perf_demo.db                              # all GET routes, slowest first
python3.11 scripts/perf_profile.py profile --db /tmp/perf_demo.db /analytics/audit           # SQL queries + costly functions
```

- The database name contains "demo" (`DEMO_MODE` guard): never `backend/data/suivi_budget.db`. Temporary databases in the scratchpad or `/tmp`.
- `bench` keeps the best of two calls: the second benefits from caches. For a cold cost, `profile` (a warm-up call then a measured call, profiler active so durations are inflated: read the proportions).
- First read the **number of SQL queries**: hundreds of queries of a few ms = N+1; few queries but a lot of time = instantiated ORM objects or Python computation.
- Browser: bytes transferred, requests, Dashboard time cold and on return (Chromium/Playwright or the built-in browser). A `localhost` does not measure a real network: say so.

References measured on 2026-11-01 (44,600 transactions): audit 117 ms, transfer suggestions 279 ms, CSV export 473 ms; Dashboard cold 2,171 → 739 ms, 1,230 → 394 KB transferred, return to the Dashboard 0 requests. A route that exceeds these orders of magnitude on the same dataset is a regression.

## 2. Backend: rules

| Situation | Rule | Model in the code |
|---|---|---|
| One query per row in a loop (`db.query/get` in a `for`) | Load the candidates for the whole batch in **one** query, match in memory (pure function in `domain/`) | `repositories/analytics/audit.py::strict_transfer_candidates` + `domain/transfers.py::strict_matches` |
| Read-only load of many rows (export, matching) | Query **columns** (`db.query(M.a, M.b)`), not ORM objects (each object loads its `selectin` relationships); fully reload only the retained rows | `repositories/budget/exports.py`, `MATCH_COLUMNS` + `load_legs` in `repositories/budget/transfers.py` |
| `async def` | Only if there is an `await`. A coroutine that works synchronously **blocks the whole server**; safeguard: `tests/garde_fous/test_async_endpoints.py` | — |
| Costly result re-read by several routes | Short cache **invalidated by writes** (see §3), never a "just in case" cache | `services/investissement/portfolio/cache.py` |
| "We need an index" | `EXPLAIN QUERY PLAN` first; fix the N+1 before. Foreign keys, `date`, `merchant` are already indexed. A composite index is only added (Alembic migration, `test_migrations.py`) if the plan shows a full scan on a **single** slow query | — |
| Full recomputation of balances (`recalculate_running_balances`, O(n) per write) | Column read + bulk `UPDATE` of only the modified rows (1 query, 0.2 s at 44,000 transactions); never ORM objects (7 `selectin` relationships) | `repositories/budget/balances.py` |
| Network call (Yahoo, Frankfurter) | Negative cache + circuit breaker + bounded concurrency; a `def` route that calls the service through `run_async` | `core/circuit_breaker.py`, `core/sync_bridge.py`, `market/quotes.py` |

Every backend fix comes with a **query-count test**: `measure_queries` fixture (`tests/conftest.py`) on a large dataset (≥ 1,000 rows), a wide bound that nevertheless fails on the N+1 (models: `tests/audit/test_data_audit_transfers.py`, `tests/budget/test_export_queries.py`, `tests/budget/test_potential_transfers_queries.py`). The test first goes red on the old code, for the right reason (the number of queries, not an import error). The returned result stays identical: snapshots intact.

## 3. Adding a cache: specification

A cache is a risk of stale data. **All** of these points are required, each tested:

1. Short duration (`TTL`), complete key (account, options, database: `id(db.get_bind())`).
2. **Invalidation on write**: `after_flush` and `after_commit` of `Session`, all sessions and background tasks included. Write through a raw connection (`exec_driver_sql`): call `invalidate()`.
3. **Generation**: a computation started before a write does not get stored (otherwise it puts the old state back in the cache).
4. **Deep copy** on entry and on exit: the caller can modify what it receives.
5. An `autouse` fixture in `conftest.py` empties it between two tests (engine ids reused).
6. Tests: 2nd call without an SQL query, write invalidates, flush without commit invalidates, modifying the copy has no effect, error not memoised (model: `tests/investissement/test_portfolio_cache.py`).

## 4. Frontend and operations

- **Read**: `api.get` serves the same URL for 30 s and de-duplicates (`lib/apiCache.ts`). Any write, logout and 401 invalidate. An "Actualiser" / "Réessayer" button or a `reload()` that **re-reads without writing** calls `resetApiCache()` first, with a failing test that counts requests (model: `src/test/pages/Audit/Audit.test.tsx`). `queryClient.clear()` is forbidden: it cancels in-flight reads (`CancelledError`).
- **Bundle**: `build.rolldownOptions.output.codeSplitting.groups` in `vite.config.ts` (Vite 8 / Rolldown, `includeDependenciesRecursively: false`: the dependencies of recharts 3 (d3, es-toolkit, Redux Toolkit…) are listed by hand in `vendor-charts`, otherwise an import cycle that only crashes in production; `manualChunks` is deprecated). After a new dependency or a new import, check the `modulepreload`s of `dist/index.html`: charts (`vendor-charts`, ~150 KB gzip) must not be there. A utility shared with recharts (`clsx`…) goes in `vendor-ui`. Compare `npm run build` before/after (gzip bytes of the initial load).
- **nginx** (`frontend/nginx.conf`): `gzip` enabled except `/api/auth/` (BREACH); do not add it to the MCP stream. Check: `docker run --rm --add-host backend:127.0.0.1 --add-host mcp-server:127.0.0.1 -v $PWD/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro nginx:alpine nginx -t`, then `curl -H 'Accept-Encoding: gzip' -I` on a file in `dist/assets/`.
- **No KPI computation on the frontend** to "save time": critical rule no. 2.

## 5. Finishing

`make validate` (lint, types, sizes, coverage, tests, build). The commit message gives the figures (`perf(audit): … ~1 s → ~130 ms at 44,000 transactions`) and the limits of the measurement. If a new cache or a new performance rule is added, update `backend/CLAUDE.md` / `frontend/src/CLAUDE.md` and this skill in the same commit.

## Rationalisations

| Excuse | Reality |
|---|---|
| "It's surely a missing index" | On this code it was an N+1: 251 queries of 4 ms. The index would not have changed the number of queries. |
| "I cache the result, it will be faster" | Without invalidation on write, it is wrong data for the duration of the cache. Specification §3. |
| "My dev database is instantaneous" | 220 transactions. Measure on the large dataset of `perf_profile.py seed`. |
| "I switch to `async` so it doesn't block" | `async def` without `await` blocks more. |
| "I regenerate the snapshot, the figure moved" | An optimisation changes no figure. A snapshot difference is a bug. |
| "The gain is obvious, no need to measure afterwards" | The first bundle split loaded the charts at entry: heavier than before. Always replay the measurement. |
| "A `reload()` doesn't need a test" | It would serve the cached response again. Test that counts requests. |

## Stop signals

`db.query` / `db.get` in a loop · `.all()` of ORM objects to read only a few columns · `async def` without `await` · cache without invalidation on write or without a copy · index added without `EXPLAIN QUERY PLAN` · `queryClient.clear()` · "Actualiser" button that re-reads through the cache · optimisation announced without a before/after figure · regenerated snapshot.
