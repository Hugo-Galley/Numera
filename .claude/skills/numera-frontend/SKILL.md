---
name: numera-frontend
description: Procedures and UI/UX standards for the Numera frontend (React, Tailwind, shadcn/ui, Recharts): adding a page, a dashboard tab, a chart, a form, handling privacy mode. Load as soon as editing frontend/src/.
---

# Numera frontend — procedures and design

Technical conventions: `frontend/src/CLAUDE.md` (read first). Slow loading, read cache, bundle: `numera-performance` skill.

## Visual identity

Sober "light enterprise" aesthetic, Tailwind + shadcn. Palette: Slate (neutral), Emerald (income, gains), Rose (expenses, losses), Amber (alerts), primary deep blue/slate (`--primary`). Titles and KPI values in `font-black`. Main content centred in `max-w-7xl`, spacing `gap-4`/`gap-6`, `space-y-4`. Light/dark themes through `UIProvider`: palettes inverted by CSS variables, hence no `dark:` variants (see `frontend/src/CLAUDE.md`).

## Presenting financial data

- `formatCurrency(amount, currency)` everywhere; coloured amounts (Emerald/Rose) rather than only signed; right-aligned in tables.
- `amount-blur` class on any sensitive amount (privacy mode).
- `Card` to group, `Badge` for statuses/categories, `Button` variants `default|outline|ghost|destructive`, `lucide-react` icons (`h-4 w-4` inline, `h-5 w-5` in a card).
- States: `Skeleton` while loading, empty state (icon + action button), `toast` (sonner) after every mutation.
- Mobile-first: hide/adapt table columns and grids with the responsive classes (see `docs/MOBILE.md`).

## Adding a page

1. `src/pages/<Name>.tsx`; beyond 350 lines, a `src/pages/<Name>/` folder: `index.tsx` (composition, early returns), hooks `use<Name>*.ts` (state, loading, actions), one component per section or dialog receiving `ctx` (model: `pages/AccountDetail/`).
2. Route in `App.tsx` (inside the `ProtectedRoute`/`AppLayout` block).
3. Entry in the Sidebar (`components/layout/Sidebar.tsx`) and in the Omnibox (`components/layout/Omnibox/`, ⌘K) so that it is discoverable.
4. Data through the functions of `lib/api/<domain>.ts` (one per route, e.g. `getAccounts<Account[]>()`, `patchAccountsById(id, body)`, `getTransactions<T>("?limit=10")`); a new route adds its function there. `api.download` for files. Never compute a KPI in the component.

## Adding a Dashboard tab

Create `components/dashboard/tabs/<Name>Tab.tsx` (current tabs: Overview, History, Budgets, Insights, Investments, Merchants, Projections, Subscriptions), wire the data in `useDashboardData.ts` (one `safeLoad` per endpoint) and declare the tab in `pages/Dashboard.tsx`.

## Adding a chart

`recharts`, palette colours, `Tooltip` and legend always present, values formatted through `formatCurrency`. Make elements clickable to navigate to the filtered view when it exists. Sankey / treemap / simulator: `components/analytics/`. World map: `components/ui/WorldMap.tsx` (`react-simple-maps` 5, hover in CSS in `styles.css`).

## React 19

Version 19: `ref` is an ordinary prop (no `forwardRef` in new code), no `defaultProps` / `propTypes`, `useRef` with an initial value, `React.JSX`. Details and exceptions: `frontend/src/CLAUDE.md`. When bumping `react` or `recharts`: check the `react-is` override in `package.json`.

## Pages to know

- `Tools.tsx`: salary management (`SalaryManager`) and remote-work calendar (`TelecommutingCalendar`).
- `Settings.tsx`: real settings only, 4 tabs (General, Notifications, Security, Data), cards in `components/settings/`. What is manipulated often does not go there.
- `Classement.tsx` (`/classement`, Management group): categories, tags, merchants, rules (`components/classement/`).
- CSV import: `components/import/ImportFlow` inside `ImportDialog`, opened from an account's page (or `/accounts?import=1`).
- `Audit.tsx`: Action Center (see `docs/ACTION_CENTER.md`); `?vue=virements` = internal-transfer review (`components/audit/TransferReview`).
- `Accounts.tsx`: account list with `AccountVerificationBanner` (updates `last_verified_at`).
- `Investments.tsx`: global view, `HoldingsTable`, `DiversityScanner`, `PointZeroModal`, `CustomEtfModal`, `SecuritySearchInput`.

## Validation

`cd frontend && npm test && npm run build` (Vitest, then `tsc` app + tests and `vite build`, currently 0 type errors); `npm run typecheck` for `tsc` alone. A fixed component or bug gets its `X.test.tsx` test (conventions: `frontend/src/CLAUDE.md` § Verification, procedures: `numera-testing` skill). Then manual check: privacy mode, dark theme, mobile width. If `vite.config.ts` or the bundle split changes: also check the **build** (`vite preview`) on a page with charts, chunk cycles only crash in production (`numera-performance` skill, § Bundle).
