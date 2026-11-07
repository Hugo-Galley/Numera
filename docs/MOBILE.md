# Mobile redesign: rules

Target: phone at 375 × 812 (also 360 px), one-handed use, thumb reach. Breakpoint: `md` (768 px); the desktop layout must **not** change visually (mobile is the default, desktop is prefixed with `md:`).

## Foundation (already in place, do not redo)
- `AppLayout`: `h-dvh`, no horizontal scroll, mobile header (brand, eye, search), `MobileNav` = fixed tab bar at the bottom (Accueil/Home, Mois/Month, Comptes/Accounts, Placements/Investments, Plus/More); `<main>` already reserves 4 rem + safe-area at the bottom.
- `DialogContent` / `SheetContent`: capped to the screen height, with internal scroll.

## Rules for every page
1. **No horizontal page scroll** at 375 px. Wide tables: either an intentional `overflow-x-auto` container, or (preferred for transaction, account and due-date lists) a **stacked card view** below `md` (`hidden md:block` table / `md:hidden` cards). Never a truncated column with no way to see it.
2. **Touch targets ≥ 40 px** (icon buttons at least `h-10 w-10`, clickable rows `min-h-11`). Space out actions that sit close together.
3. **Grids**: `grid-cols-1` by default, `sm:grid-cols-2`, then `lg:`/`xl:`. KPIs: 2 columns max on mobile.
4. **Page headers**: title + actions that wrap (`flex-col gap-3 sm:flex-row sm:items-center sm:justify-between`); action buttons full width or icon-only below `sm`.
5. **Tabs** (`Tabs`): horizontally scrollable list (`overflow-x-auto`, no wrapping), active tab kept visible.
6. **Forms / dialogs**: full-width fields, `text-base` (16 px) on `input` to avoid iOS zoom, footer buttons stacked (`flex-col-reverse sm:flex-row`), keyboard: the primary button stays reachable (the dialog scrolls).
7. **Recharts charts**: `ResponsiveContainer` height ≤ 260 px on mobile, fewer axis labels (`interval="preserveStartEnd"`, `tick` 11 px), legend below the chart, readable tooltips. No chart wider than the screen.
8. **Text**: `truncate` / `break-words` on merchant labels, `min-w-0` on flex children that contain long text. Amounts: never truncated (`whitespace-nowrap tabular-nums`).
9. **Dropdown menus / popovers**: stay within the screen (`collisionPadding`, `max-h` + scroll).
10. Page padding: the container applies `p-4`; do not add negative margins that overflow.
11. Privacy mode, dark theme, `formatCurrency`: unchanged (see `frontend/src/CLAUDE.md`). No KPI computed on the frontend.

## Verification (mandatory)
- Demo backend: `http://localhost:8011` (throwaway database), frontend: `http://localhost:5173` (already running, `VITE_API_BASE` points to 8011). Login `admin` / `demo1234`. Do not start another server, do not touch port 8001.
- Built-in browser: `resize_window` to 375 × 812 (`preset: mobile`), open every screen in your scope **including its dialogs and tabs**, take a screenshot, and fix. Measure overflow: `document.documentElement.scrollWidth > window.innerWidth` must be `false`.
- `cd frontend && npm run typecheck` with no error. Put the viewport back to `desktop` at the end and check that a desktop page has not moved.
- Only modify the files in your scope (not `components/layout`, `components/ui`, nor `docs/MOBILE.md`). If a shared fix is needed, describe it in your report instead of making it.
- No commit: the commit is made by the main agent.
