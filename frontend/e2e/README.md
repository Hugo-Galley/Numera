# E2E tests (Playwright)

End-to-end critical journeys: real browser, real frontend (Vite), real backend.
They complement Vitest + MSW (which mocks the API) and the pytest tests: they catch what mocks cannot see
(front ↔ back contract, JWT auth, redirects).

```bash
make test-e2e                 # or: cd frontend && npm run test:e2e
cd frontend && npx playwright test login --ui    # one scenario, in interactive mode
cd frontend && npx playwright show-report        # report (CI); trace: npx playwright show-trace <trace.zip>
```

First run: `cd frontend && npx playwright install chromium`.

## Scenarios

| File | Checks |
|---|---|
| `login.spec.ts`, `logout.spec.ts` | login, wrong password, return to the requested page, logout |
| `navigation.spec.ts` | every route loads: no blank page, JS exception, console error or 5xx |
| `import-csv.spec.ts` | preview, import, visible rows, re-import without duplicates |
| `transaction.spec.ts` | manual entry of a transaction |
| `rules.spec.ts` | creation and deletion of a categorisation rule |
| `privacy.spec.ts` | privacy mode (enable, persistence, disable) |

New route in `App.tsx`: add it to `ROUTES` in `navigation.spec.ts`.

## How it works

- `playwright.config.ts` starts two servers: the backend (`e2e/backend.sh`) on **8101** and Vite on **5174**
  (ports distinct from dev, so E2E can run during a `make dev`).
- `e2e/backend.sh` regenerates `backend/data/e2e-demo.db` on every run (demo mode, credentials `demo` / `demo`,
  file ignored by git). The real database is never touched. `E2E_PYTHON=...` forces the interpreter.
- `auth.setup.ts` logs in once; scenarios reuse the session. A scenario that tests login
  starts from a clean browser (`test.use({ storageState: { cookies: [], origins: [] } })`).
- A single worker: scenarios that write share the same database.

## Writing a scenario

- Selectors by role / label (`getByRole`, `getByLabel`), never by CSS class.
- Explicit waits (`expect(...).toBeVisible()`), no `waitForTimeout`.
- Data created by the scenario uses an `E2E ` prefix; dates are relative to today.
- Few scenarios, critical journeys only; no reference screenshots.

## README screenshots

`npm run screenshots` regenerates `docs/screenshots/*.png` (1440×900 at @2x) on the throwaway demo database. Ignored by `npm run test:e2e`.
