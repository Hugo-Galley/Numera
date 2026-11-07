---
name: numera-tdd
description: Use when about to write or change backend code in Numera (feature, bug fix, KPI, audit rule ("règle d'audit"), import, behaviour refactor), before touching backend/app/, or when tempted to "test afterwards" ("tester après") / "just fix it quickly" ("juste corriger vite").
---

# Numera — mandatory TDD

## Principle

**Not a single line of `backend/app/` without a test that fails first, for the right reason.**
Violating the letter of this rule is violating its spirit. Full cycle: `superpowers:test-driven-development`; this skill says how to apply it here.

## The cycle in Numera

1. **RED** — write the test, run it alone, see it fail:
   ```bash
   cd backend && PYTHONPATH=. python3.11 -m pytest tests/<domain>/test_<subject>.py::test_<case> -v
   ```
   The failure must be an **assertion** on the expected behaviour (not `ImportError`, not `401`, not a broken fixture). A test that passes the first time proves nothing: fix it or write another.
2. **GREEN** — the minimal code that makes this test pass. Nothing else.
3. **REFACTOR** — clean up (layers, names, duplication), tests green at every step. Then the full suite: `make test`.

## Which test level

| What you change | Where the test goes | Fixture |
|---|---|---|
| Pure calculation (`domain/`) | `tests/<domain>/test_domain_<subject>.py` | none: in-memory objects (model: `test_domain_transfers.py`) |
| Use case (`services/`) | `tests/<domain>/test_<subject>_service.py` | `db_session`, no HTTP |
| Contract of a route | `tests/<domain>/test_<subject>.py` | `client` + re-read from the database |
| Analytics / portfolio figure | targeted test **in addition to** the snapshots | — |

The lowest level that expresses the behaviour wins. A calculation that is hard to test without a database is a calculation that is not yet in `domain/`: the test tells you where to put it (see `numera-clean-architecture`).

## Assertions that matter

- Effect in the database, not only the HTTP code. For an expected commit, re-read in a **fresh session** (`_fresh_balances` in `test_balances_service.py`).
- Balances (`running_balance`) after any transaction mutation; positions after any security operation.
- Frozen dates (`freezegun`) as soon as a calculation depends on "today".
- Network: forbidden in tests (`block_network`). Patch `integrations/…`, never disable the guard.

## Bug = reproduction test first

Reported bug → `superpowers:systematic-debugging` for the cause, then a test that **reproduces** the bug and fails, then the fix. Name the test after the behaviour (`test_transfer_between_same_account_is_never_paired`), not after the ticket.

## Snapshots (`tests/snapshots/`)

A snapshot difference is a red test like any other. Never `UPDATE_SNAPSHOTS=1` to make the suite pass. Only when the figure change is **intended**: a targeted test first demonstrates the new figure, then regeneration, and the commit says why the figure changes.

## Frontend

Frontend tests (Vitest, `numera-testing` skill) check rendering, calls and journeys, not business rules: no logic lives there. A rule to test on the front side (calculation, aggregate, status) → it belongs to the backend, in TDD. A fixed frontend bug follows the same discipline: failing `X.test.tsx` first.

## Rationalisations

| Excuse | Reality |
|---|---|
| "Too simple for a test" | Audits A2–A12 were "simple" duplicated calculations. 30 s of test. |
| "I'll write the tests afterwards" | A test written afterwards passes immediately: it proves nothing. |
| "The snapshot already covers that" | The snapshot says *that* it changes, not *what* is right. Targeted test. |
| "It's a refactor, no behaviour" | Then the existing tests must stay green without modification. If they must change, it is a behaviour change → RED first. |
| "I tested by hand in the UI" | Not reproducible, not versioned. Write the test. |
| "I'll keep the code already written as a reference" | Delete it. Start again from the test. |
| "The user is in a hurry" | A fix without a test comes back in an audit. The test *is* the fast path. |

## Stop signals

Code written before the test · test never seen red · test red for the wrong reason · snapshot regenerated without a targeted test · "I'll test at the end". → Delete the code, go back to RED.
