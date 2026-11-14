# E2E tests (Playwright)

End-to-end user journeys: real browser, real frontend (Vite), real backend on a throwaway demo database.
They complement Vitest + MSW (which mocks the API) and pytest: they catch what mocks cannot see
(front ↔ back contract, JWT auth, redirects, invalid HTML, console errors).

```bash
make test-e2e                                   # the whole suite (~4 min), or: cd frontend && npm run test:e2e
cd frontend && npx playwright test accounts     # one file; -g "pattern" for one scenario; --ui for interactive mode
cd frontend && npx playwright show-report       # HTML report; trace: npx playwright show-trace <trace.zip>
```

First run: `cd frontend && npx playwright install chromium` (and `make backend-install` for the backend).
Locally, servers already running on 8101 / 5174 are reused (fast iteration); in CI (`CI=true`) the stack
is always started from scratch.

## Scenarios (by journey)

| File | Journey |
|---|---|
| `login`, `logout` | login, wrong password, return to the requested page, logout, expired session (401) |
| `dashboard` | KPIs of the month, tabs, account filter, month change, dark theme, privacy mode (`privacy`) |
| `accounts` | list, account page, creation / edit / archiving, bank reconciliation |
| `transactions` | entry, edit, deletion with confirmation, search and filters, internal transfer |
| `import-csv` | preview, import, visible rows, re-import = no duplicate (idempotence) |
| `classement`, `rules` | categories, tags, merchants, categorisation rules |
| `month` | month summary, comparison, end-of-month review and closing (mark, never lock) |
| `investments` | global view, securities account (positions, search), Zero Point, life insurance |
| `savings`, `recurring`, `loans-reimbursements` | goals, recurrences and calendar, salary, loan, "owed to me" claims |
| `audit` | Action Center, refresh, internal transfers |
| `settings` | four tabs, security, CSV export, danger zone, profile |
| `tools` | simulator, taxation, yearly review |
| `omnibox` | ⌘K: navigation, accounts, closing |
| `security/*` (`security` profile) | TOTP 2FA (enabling, login, single-use recovery code, regeneration, disabling), passkey (virtual WebAuthn authenticator), MCP tokens (shown once, GET ok / POST 403, revocation), encrypted backup and restore, ntfy / Telegram notifications |
| `responsive`, `navigation` | sidebar, 404, redirects, mobile 375 px without overflow, **every route loads** |

The **cross-cutting guard** (automatic fixture, `fixtures.ts`) fails any scenario that causes a JS exception,
an application console error (including the invalid HTML reported by React) or an HTTP 5xx response, on
any page. A scenario that expects a specific error declares it: `test.use({ ignoredErrors: [/pattern/] })`.


## How it works

- `playwright.config.ts` starts the backend (`e2e/backend.sh`, port **8101**) then Vite (port **5174**), distinct from
  dev: E2E can run during a `make dev`.
- `e2e/backend.sh` regenerates `backend/data/e2e-demo.db` on every run (demo mode, credentials `demo` / `demo`,
  ignored by git). The real database is never touched. Demo mode blocks 2FA, passkeys, MCP tokens, backups and
  notifications and caps writes at 120 per minute: these areas belong to the `security` profile (below).
- `auth.setup.ts` logs in once (`storageState`); all scenarios reuse the session. A scenario that
  tests login starts from a clean browser (`test.use({ storageState: { cookies: [], origins: [] } })`).
- A single worker per stack (shared database). CI runs **a single job** `E2E (Playwright)` (projects `chromium` and
  `security`, two stacks); on failure, the HTML report + traces + screenshots are published as the `playwright-report`
  artifact (7 days). `retries: 1` in CI only.
- Demo data is dated relative to today (same day, same data): never assert a demo amount,
  only its presence or its structure. The amounts of entries created by the scenario, however, are known.

## `security` profile (areas blocked in demo mode)

`DEMO_MODE` refuses these routes (`services/systeme/demo/guard.py`); instead of weakening the demo, a second
Playwright project (`security`, preceded by `setup-security`) runs on a **dedicated, non-demo stack**:

| Building block | Role |
|---|---|
| `backend-security.sh` (port **8102**) | throwaway database `backend/data/e2e-security.db` (recreated on every run, blank: default categories only), credentials `e2e` / `e2e-security-pass`, throwaway `BACKUP_DIR` and public test Fernet key, `LOGIN_MAX_ATTEMPTS=100` |
| Vite (port **5175**) | same frontend, `VITE_API_BASE` pointing to 8102 |
| `mock-external.mjs` (port **8103**) | fake ntfy server (`POST /`) **and** HTTPS proxy (the backend's `HTTPS_PROXY`) that logs then refuses every `CONNECT`; log read by the tests (`GET /__requests`): no real network call, Telegram (fixed address `api.telegram.org`) is seen there without going out |

The specs are in `e2e/security/` (import `test` from `../fixtures`, helpers from `./support`). Method notes:

- **TOTP**: `totpCode(secret, offset)` implements RFC 6238 on the test side. The code of the current step is used for enabling (the
  backend marks it as consumed); logins use step +1 (within the ±1 window), step −5 is outside the window. No
  waiting, independent of the second of execution. Each test of `totp.spec.ts` is independent: `resetTwoFactor()` (before and
  after, clears the 2FA settings of the throwaway database) then `enableTwoFactor()` (enabling through the API); retries and order have no effect.
- **Passkeys**: Chromium virtual authenticator (`WebAuthn.addVirtualAuthenticator` through CDP), `localhost` is a secure context.
- **MCP tokens**: the plain value is only checked at creation; a token that writes (`POST`) gets 403, a revoked token 401.
- **Backup**: the button triggers `scripts/backup.py`; the test reads the `.enc` back with `scripts/restore.py` (restore has no screen).
- **Intended 5xx**: the Telegram test send answers 502 (channel unreachable); `test.use({ expectedServerErrors: [/URL pattern/] })`.
- Stacks reused locally: scenarios cope with a database already used (unique values, relative counting, 2FA reset).
- Python for the scripts (restore, 2FA reset): `backendPython()` resolves `E2E_PYTHON` (relative to `backend/`, as in CI) to an absolute path.

## Writing a scenario

1. Import `test` / `expect` from `./fixtures` (never `@playwright/test`: the guard and the neutralisation
   of the month-closing pop-up would be lost). Helpers: `openAccount`, `openTransactionMenu`, `confirmDialog`, `visible`, `unique`.
2. Selectors by role / label (`getByRole`, `getByLabel`), never by CSS class; `data-testid` only when there is
   no accessible selector. Lists have two layouts (mobile cards / table): `visible(page, text)`.
3. Explicit waits (`expect(...).toBeVisible()`, `waitForResponse`), never `waitForTimeout`.
4. Data created with `unique("Subject")` (`E2E ` prefix + time suffix): the scenario can be re-run on the same database,
   and cleans up after itself when the write is reversible.
5. New route in `App.tsx`: add it to `ROUTES` in `navigation.spec.ts`.
6. A failing test reveals a bug: do not write a test that accepts it; fix it or mark it `test.fail` with the reason.

## README screenshots

`npm run screenshots` regenerates `docs/screenshots/*.png` (1440×900 at @2x) on the throwaway demo database. Ignored by `npm run test:e2e`.
