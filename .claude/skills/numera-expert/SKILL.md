---
name: numera-expert
description: Business-domain knowledge of Numera (budget + investments): calculation rules, internal transfers, zero point, salary/remote work, merchants, Action Center, CSV import. Load before touching financial logic, a KPI, an import or an audit rule.
---

# Numera — business logic

The short critical rules are in the root `CLAUDE.md`; this skill details the mechanisms that require reading several files. French identifiers (`Entree`, `Sortie`, `versement`, `achat`, `Point Zéro`…) are the literal values stored in the database or shown in the UI.

## Balances and transaction types

- `transactions.amount > 0` always; `type` ∈ `Entree | Sortie | Interets | Solde Initial`. Impact on the balance: `domain/finance.py::apply_transaction_to_balance` (`Solde Initial` replaces the balance, it is neither income nor expense).
- `running_balance` is stored and fully recomputed by `services/budget/balances.py::recalculate_running_balances(db, account_id)` after any mutation, bulk operation, transfer link/unlink and import.
- Investment: `investment_transactions` (`versement | retrait` = cash flows counted in the invested amount; `achat | vente` = security operations; `dividende`; `frais`), `balance_snapshots` for the entered value; `portfolio_holdings` for positions (ticker, ISIN, quantity, average cost (PRU) fees included, `cost_basis_eur`) linked to an `etf_profile`.
- Derived positions: Zero Point inventory (`holding_baseline_items`, dated by `accounts.holdings_baseline_date`) + later security operations, recomputed by `services/investissement/holdings/rebuild.py::rebuild_holdings` (upcoming operations ignored, rule 12; the hourly task calls `rebuild_due_holdings` when one comes due). A security operation before the Zero Point is refused; to fix a starting PRU or quantity, edit the inventory row (`PUT /holdings/{id}`).
- Dividends: `type = dividende` with mandatory ticker; `amount` = net received, `withholding_tax` informational, `reinvested` creates a linked `achat` (`reinvest_of_id`). **Manual** entry (the broker's amount is authoritative, no Yahoo detection). EUR aggregates: `services/investissement/dividends.py` + `domain/dividends.py`, `GET /analytics/dividends`. Dividends do not count in the invested amount.
- Missing PRU on a Zero Point row: `services/investissement/holdings/cost_estimates.py::estimate_baseline_costs` infers it from purchases before the inventory (price × quantity, or, for old deposits with no security or quantity, the deposited amount attached by label ÷ shares held) ("Estimer les PRU" button, manual validation).
- Value of a securities account (PEA/CTO/crypto) = positions × price + cash (`services/investissement/portfolio/`, `GET /analytics/portfolio[/{id}]`); life insurance and accounts without positions = last snapshot. **Single source** for the current value: `services/investissement/portfolio/compute.py::positions_values_eur`, used by `patrimoine-allocation`, `budget` (current period, life insurance included in `patrimoine_net_total`) and `investments-allocation`; past months keep the last dated statement. Snapshots serve reconciliation (gap > 2 % → Action Center). Unrealised gain with currency effect, realised gain per year (basis of the French form 2074), XIRR and TWR are computed on the backend.
- Prices: stored in `security_prices` (one close per ticker per day), the last known price serves as a fallback (`stale`) if Yahoo does not answer.

## Income and net worth (single definitions)

- **Income**: `income_criterion(db)` (`repositories/analytics/common.py`, query joined to `Account`) = inflow on a `courant` account, or an inflow whose category is of type `revenu` (explicit marking of income that arrived elsewhere), or `Interets`. `Solde Initial` and internal transfers never. The money-flow reuses the budget's `revenus_totaux`; the Sankey, timeseries and `kpi-history` apply the same criterion. An unlinked deposit on a savings account is therefore not income.
- **Flow scope** (income/expenses, breakdown by category, top merchants, Sankey): `courant` and `epargne` accounts excluding meal vouchers; `expenses-by-category` adds a "Sans catégorie" (uncategorised) block so that its total equals `depenses_totales`.
- **Net worth** (*patrimoine*): `services/comptes/wealth.py::account_values(db, accounts, at=None)` → value per account (positions × price for a securities account valued that way; otherwise statement; for checking/savings/other the more recent of statement and last balance; nothing = 0). Also used by the Accounts page (`account_balance`), `/tax/overview`, the diversity scanner, the cash-flow projection, the month review and `/analytics/investments` (`use_positions=False`, statements only). Used by `patrimoine-allocation`, `investments-allocation(-advanced)` and `budget.patrimoine_net_total` (all active accounts, including the old type `bank`).
- **Loans**: a `credit` account (created through `/loans`, never through `/accounts`) is worth −remaining principal of its loan (`domain/loans.py` (`loan_remaining`: `services/comptes/loans.py`)): all net-worth totals are therefore **net**. `patrimoine-allocation` takes loans out of the pie chart (`total_debts_eur`, `net_patrimoine_eur`). No transactions on a loan account: instalments stay `Sortie` entries of the checking account (normal expenses).
- **Pay month**: `build_periods` fills the gaps (a month without salary = its own window, a second salary in the same month absorbed) so that every day belongs to a period.

## Upcoming transactions

A transaction dated after today is an upcoming entry: `running_balance` computed chronologically like the others, but excluded from any balance and total "as of today". Bounds: `core/time.py::end_of_today()` (tomorrow 00:00, exclusive; an expense of the day counts whatever its time); `budget_period.period_bounds` caps the monthly window at that bound, `budget_period.period_window` gives the whole window (display). Reads of the last balance (`account_balance`, cash-flow projection, diversity scanner, value of a securities account without a statement) pass `before=end_of_today()`. CSV import: keeps the last real transaction (no cap) to chain the balance.

Display: `TransactionRead.is_upcoming` (computed field) and `is_upcoming` of the calendar events come from the backend, the frontend never compares dates. `/analytics/cashflow-projection` merges upcoming entries (`scheduled`) and projected recurrences (`recurring`); the "À venir" (upcoming) card (`pages/AccountDetail/UpcomingCard`) reads it for a checking or savings account.

## Internal transfers

A transfer is a **1-to-1** pair: a `Sortie` and an `Entree` (or an investment `versement`) on two different accounts (`is_transfer`, `linked_transaction_id` / `linked_investment_transaction_id`). A link changes no amount. "Real expenses", income and the savings rate exclude these rows (`services/analytics/metrics/`, `services/analytics/budget/`). All the logic is in `services/budget/transfers.py`:

- `link_pair` / `unlink_pair`: the only entry point to link or unlink (endpoints `POST /transactions/{id}/link/{other_id}`, `.../unlink`); `link_pair` refuses (`BusinessRuleError`, 422) any pair that is not a `Sortie` + an `Entree` (or a `versement`) on two different accounts. `PATCH /transactions/{id}` no longer accepts `is_transfer` or `linked_*`. `link_origin` = `manual` | `rule` | `recurring`; `transfer_rule_id` = originating rule.
- **Unlinking a `rule` or `recurring` link** marks both rows `is_transfer_ignored`, otherwise the rule would immediately link them again. An unlinked manual link is not ignored.
- `find_pairs`: global 1-to-1 matching (date gap, then amount gap), an inflow is never used for two outflows; perfect ties are returned `ambiguous=True` and never linked alone. Used for suggestions (`GET /transactions/potential-transfers?months=`, whole history by default, ±5 days and ±1 % adjustable from the Transfers tab) and for rules.
- `transfer_rules` (`/transfer-rules`): source account → destination account, optional `pattern` (outflow's merchant/note), optional `amount`, tolerances (1 % / 5 days by default). `apply_rules` links unambiguous pairs; triggered after a CSV import, the creation/modification of a transaction and the generation of recurrences (3-month window, `auto_link_transfers` never fails), and over the whole history by `POST /transfer-rules/apply` (`dry_run=true` for a preview).
- "Transfer" recurrence: `recurring_transactions.transfer_to_account_id` (Sortie from a non-securities account) → each due date creates the outflow **and** the inflow/deposit (`create_counterpart`, currency conversion, balances recomputed), linked with `link_origin = recurring`. With a ticker (`investissement` destination only), the inflow leg is a `versement` with a security: deposit **and** purchase of shares in one operation (cash neutral, counted once in the invested amount), `rebuild_holdings` rerun. Two existing recurrences (one per account) are linked by a rule. The "À venir" projection and the calendar count the inflow on the destination account (destination currency, `transfer_credit_date`); in the calendar's global view, a transfer to a counted account is ignored (neutral). Delayed arrival (`transfer_credit_day`, e.g. debit on the 29th, PEA credited on the 16th): the outflow stays in transit (`transactions.transfer_credit_due`), the inflow/deposit (and the purchase at that day's price) is created by `_credit_pending_transfers` once the date has passed; due date dropped without credit if the outflow was linked or unlinked in the meantime.
- Manual linking: `GET /transactions/{id}/transfer-candidates` (±15 days, ±5 %, all accounts) and `POST /transactions/{id}/transfer-counterpart` (creates the missing inflow). UI: `TransferLinkDialog` (button on each `AccountDetail` row); rules in Management › Classement › Rules, suggestions and linked transfers in Action Center › Internal transfers (`/audit?vue=virements`).

## Splits, provisions, archiving

- **Split** (`services/budget/splits.py`, `PUT /transactions/{id}/splits`): a non-transfer `Sortie` divided into parts whose sum equals the amount; never an Investissement/Epargne or `revenu` part (otherwise real expenses would change). The transaction takes the category of the largest part. Every **category** breakdown goes through `repositories/analytics/common.py::category_lines()` (one row per part, reimbursement pro rata) instead of `Transaction.category_id`; totals do not depend on it.
- **Provisions** (`services/budget/provisions.py`, `/provisions`): purely forward-looking (no transaction). Monthly effort = (amount − accumulated) ÷ remaining months; accumulated = balance of the linked account split in proportion to targets, otherwise theoretical.
- **Archiving**: `categories.archived`, `tags.archived` (hidden from selectors with `?include_archived=false`, nothing changes in history or analytics); an archived account = `accounts.active = False` (`DELETE /accounts/{id}`, reactivation through `PATCH active=true`).

## Reimbursements

A `Sortie` carries **claims** (`reimbursement_claims`: free-form debtor, expected amount); `Entree` rows are **allocated** to them with an amount (`reimbursement_allocations`, several inflows per claim and several claims per inflow). Everything goes through `services/budget/reimbursements.py`, which recomputes `transactions.reimbursement_offset` (Sortie: total received; Entree: total allocated).

- Income/expense KPIs are **net** on the month and category of the expense: `NET_AMOUNT = amount − reimbursement_offset` (`repositories/analytics/common.py`) in budget, budget-alerts, expenses-by-category, top-merchants, tags, kpi-history, timeseries, monthly-report, money-flow, sankey, insights. Stay **gross**: balances, account-flow-summary, calendar, cashflow-projection, subscriptions, tax, salary series.
- Rules: Sortie ↔ Entree, same account currency, never an internal transfer (and `find_pairs` / `candidates_for` / manual linking exclude these transactions), caps (claims ≤ expense, allocations ≤ expected and ≤ inflow, rounded to the cent), expected never below received. Changing the type or lowering the amount of a linked transaction is refused (400); deleting one frees the other (`detach_before_delete` + `sync_offsets`).
- Write-off: bring the expected back to the received, or delete the claim. No cash, no automatic linking (candidates: debtor in the label, then exact amount, then date; −7 days / +180 days).
- Action Center: `unallocated-reimbursements` ("Remboursement…" inflows of the last 180 days not allocated, if an open claim exists).

## Zero Point and performance

A single `is_zero_point` per investment account (`POST /balance-snapshots/set-zero-point`). Performance: securities account = computed value (positions × price + cash, `services/investissement/portfolio/`) − invested amount; life insurance = last snapshot − Zero Point baseline − flows (`services/analytics/investments/flows.py`). Advanced allocation and the diversification scanner use `etf_profiles` (countries/sectors/top holdings as JSON text). Sectors and top 10 come from Yahoo (weekly refresh); countries are never provided by Yahoo (preset of system profiles or manual entry). No composition is guessed: an unknown field stays empty and its share is counted as "Non renseigné" (not provided).

## Merchants and categorisation

- `merchant` = raw bank label, never modified. `merchant_id` → canonical `merchants` through `merchant_aliases` (`POST /merchants/auto-normalize`, `GET /merchants/suggestions/unnormalized`).
- `categorization_rules`: case-insensitive `pattern` on merchant/note, `priority` descending, `POST /categorization-rules/apply-all`. The import also applies the rules.

## Recurrences, subscriptions, salary

- `recurring_transactions`: `frequency` (monthly/weekly/quarterly/yearly), `excluded_months`, `auto_generate`. Generation by `services/budget/recurring.py` (hourly background task + `POST /recurring-transactions/trigger`). Can also carry security purchase rows (ticker, quantity, price). Quantity or price not fixed: the price is the **close of the due-date day** (`services/investissement/market/quotes.py::get_price_on`, including for caught-up due dates), falling back to the live quote, quantity = amount ÷ price (`services/budget/recurring.py::_size_trade`). `whole_shares` option (PEA: the broker only executes whole shares): quantity rounded down to the integer and the deposit's `amount` = shares × price; the bank outflow stays at the planned amount (the remainder stays as cash at the broker, as in reality); amount < price of one share → fractional quantity. The closing price remains an estimate: the broker's real execution may differ by ~1 %, hence the need to check the deposited amount against the broker's export.
- Subscriptions detected dynamically (`/analytics/subscriptions`), ignorable (`is_subscription_ignored`).
- Salary: `salary_configs` (salary/voucher accounts, net, voucher value, employee share), `telecommuting_days` (remote-work days), `salary_months` (`is_generated`). `POST/DELETE /salary/generate/{year}/{month}` creates / deletes the transaction. `services/budget/salary_generation.py` generates **a single** "Salaire" transaction = `net_salary − remote_days × ticket_employee_share` (no voucher transaction: vouchers are informational); idempotent.
- Price in working hours: `services/budget/work_time.py` (rate: `domain/salary.py::hourly_rate`), `GET/PATCH /salary/work-time` → net hourly rate = `net_salary × 12 ÷ (work_days_per_year × work_hours_per_day)` (settings in `system_settings`, 218 days × 7 h by default, `net_salary` before voucher deduction). The frontend divides an EUR amount by this rate for display (`components/ui/work-hours.tsx`, `WorkTimeProvider` context): `AccountDetail` expenses (net of reimbursements, excluding transfers, EUR accounts), subscriptions, top merchants.

## Benefits received

`benefits` (`/benefits`, Échéances › Salaire › Aides tab, `?tab=salary&vue=aides`): activity bonus, housing aid… Payments are found among inflows whose label or note contains `match_pattern` (attached to the benefit with the closest amount if several match). Month status, changed amount and declaration reminder (activity bonus: quarterly, "Déclaration faite" moves the due date forward) → Action Center and notifications. Benefits stay ordinary income (rule 11); no computation of CAF entitlement. **Generation** (`auto_generate`, receiving account required): `services/budget/benefit_generation.py` creates on the payment day a provisional `Entree` (`is_provisional`, expected amount, the benefit's logo); the CSV import and the hourly task call `reconcile_provisional`, which replaces it with the real payment (label containing the pattern, ±10 days) without an income duplicate. A provisional entry is never a received payment.

## Pay month

`services/budget/budget_period.py` (pure calculation: `domain/budget_period.py`): a salary received opens a period (until the next salary) named after the month it finances (salary of 25 August → September; name = month of `start + 15 days`). Every monthly window computation must go through `period_bounds(db, year, month)` (never `datetime(year, month, 1)`), and every grouping by month through `period_key_expr` (never `strftime("%Y-%m")`). Setting `budget_month_mode` (`civil` | `salary`, default `salary`), `GET/PUT /analytics/budget-period`. Dates and balances do not change. Yearly review `/wrapped`: forced to calendar months (`civil_months()`).

## CSV import / export

Mandatory columns: `Date`, `Commercant`, `Montant` (header aliases in `HEADER_ALIASES`); `Type`, `Categorie`, `Mois`, `Note` optional. Amount: the decimal separator is the last of "," / "." (1,234.50 = 1.234,50); a signed amount is accepted: explicit `Type` takes priority, otherwise negative = Sortie, positive = Entrée (the stored amount is always positive). A `Solde Initial` at 0 is accepted, other zero amounts are not. `POST /import/preview` (no write; returns `invalid_rows`, `warnings` and, per row, `line` + `error`) then `POST /import/commit` (returns `error_details` = `[{line, reason}]` in French; empty rows ignored); idempotent on the file's **raw** `(account_id, date, amount, merchant, type)`, kept in `transactions.original_merchant` / `original_type` (stable despite rules and manual edits; older rows: stored values); categorisation rules never touch `merchant` (`merchant_name` → `merchant_id`), duplicate detected **before** any category creation; file ≤ 10 MB; `imports_log`; final balance recomputation. Export: `GET /export/transactions.csv` (Numbers format).

## Merchants

Creating a merchant with aliases, or adding an alias, immediately attaches the non-normalised transactions whose bank label is that alias (`merchants._link_matching_transactions`). Non-empty, unique name and alias (409 otherwise). Normalisation suggestions ignore transfers and the Investissement/Epargne categories.

## Action Center (`/analytics/actions`, page `Audit.tsx`)

Aggregates: integrity audit (`/analytics/audit`, issues with stable `id`: `uncategorized-expenses`, `missing-merchants`, `unnormalized-merchants`, `duplicate-transactions`, `missing-initial-balances`, `stale-investment-snapshots`, `unused-categories`, `unmatched-transfers`), budget alerts (`/analytics/budget-alerts`) and rule suggestions. `ActionItem.action_type` drives the modal on the frontend (`link`, `modal_categorize`, `modal_rule`, `modal_snapshot`, `modal_merchant`). Dismissed items are persisted (`POST /analytics/actions/dismiss`, `dismissed_insights`). Adding an action: see `docs/ACTION_CENTER.md`.

## Account verification and reconciliation

`accounts.last_verified_at` is updated by `POST /accounts/{id}/verify` ("Rien n'a bougé" of `AccountVerificationBanner`) or by `POST /accounts/{id}/reconcile` when the balance entered by the user equals (± 0.01) the end-of-day `running_balance`. Otherwise the reconciliation (`services/comptes/reconciliation.py`, read-only, 60 days before the date) suggests leads: duplicate (same label, direction and amount within ≤ 3 days), a row whose amount equals the gap, a row whose direction inversion closes the gap, otherwise a missing transaction. Nothing is corrected automatically.

## Subscription price increases

`services/budget/subscription_prices.py::detect_price_changes` (series detection: `domain/subscription_prices.py::series_change`): series of regular outflows (recurrence, otherwise canonical merchant, otherwise label, per account), monthly / quarterly / yearly cadence, increase ≥ 0.10 and ≥ 1 % against a stable previous amount. Exposed in `price_changes` of `/analytics/subscriptions` and in the Action Center. A decrease is not flagged.

## Decision journal

Table `financial_events` (`/financial-events`): dated notes with no effect on any calculation, ⚑ markers on the History tab curve with the highlights of closures (`month_closures.highlight`). Placed in their calendar month (the `kpi-history` label may follow the pay month).

## Taxation and wrappers (`/tax`, page `Tax.tsx`)

`accounts.tax_wrapper` (`pea`, `per`, `cto`, `assurance_vie`, `livret_a`) and `opened_at` enable tracking. Rules in `domain/tax.py`, figures only in `domain/tax_rules.py` (table per year, to verify every year). These are French tax wrappers:

- **PEA**: cumulative deposits (sum of `versement`) against €150k; a withdrawal does not give room back; withdrawal before 5 years = alert; alert if the account starts from an inventory / Zero Point (earlier deposits not entered, remaining room overestimated).
- **PER**: deposits of the calendar year of **all active PERs added together** (household ceiling, a single card) against the deduction ceiling = 10 % of N-1 professional income bounded between a floor and a maximum; tax saving = deductible amount paid × marginal tax bracket (TMI).
- **Livret A**: current balance of the account against the ceiling ("ceiling reached" alert: capitalised interest may legitimately exceed it).
- **Livret Jeune**: same against €1,600; the age (12-25) is not checked.
- **PEE** (`pee`): each `versement` is locked for 5 years (`retrait` rows are applied to the oldest) → total paid, locked, available, next unlock; ceiling of voluntary deposits of the year = 25 % of annual gross salary (setting `tax_gross_annual_salary`). A deposit whose note contains "abondement" is the employer's matching contribution: it counts in the total and in the lock, never in the ceiling. No tax computed (the PEE social-contribution rate is not confirmed).
- **Life insurance** (*assurance-vie*): seniority against 8 years and the yearly allowance reminded (single / couple); the gain share of a withdrawal is not computed.
- **CTO** (taxable securities account): the only account concerned by the yearly recap: gross dividends (net + withholding, box 2DC), realised gains (3VG) or losses (3VH) from the `replay_account` replay (no network call), tax estimated at the flat tax (PFU) by category (`pfu_rate_dividends` and `pfu_rate_gains`, because the CSG increase to 10.6 % applies from 2025 income on capital gains but only from 1 Jan 2026 on dividends: in 2025, 30 % on dividends and 31.4 % on gains; 31.4 % everywhere in 2026; life insurance stays at 17.2 %); a loss does not offset dividends. Sales with no known cost basis: flagged, never silently counted as zero.
- Settings (`system_settings`): `tax_tmi_pct`, `tax_prior_year_pro_income`, `tax_household`, `tax_gross_annual_salary`.

## End-of-month review (`/month-review`, page `MonthReview.tsx`)
- Closing = **marking** (table `month_closures`, snapshot `tx_count`/`income`/`expenses`/`unresolved_count`), never locking: late CSV imports and reimbursements remain possible. `modified_since_close` compares the transaction count and the fingerprint (inflow/outflow totals per account currency, without conversion) with the recomputation: exact, insensitive to exchange rates; no `updated_at` on `Transaction`, so a simple category change is not detected (intended).
- `transactions.is_exceptional`: the expense stays in official totals and `running_balance`; only the `*_excl_exceptional` reads isolate it. The "Investissement" / "Epargne" categories are excluded from the calculation (already outside `depenses_reelles`). Budget alerts and end-of-month projection are **not** concerned.
- The "categorise" step is bounded to the month (the Action Center `/analytics/actions` is global: do not reuse it as is).

## Savings rate and resilience
`savings` (monthly report, month review) = `services/budget/month_review.py::savings_basis` = income − real expenses in global view: same numerator as `taux_epargne`. Resilience (`services/analytics/budget/resilience.py::compute_resilience`, `GET /analytics/resilience`) = liquid savings ÷ average real expenses of the last 6 **complete** months (never the current month); the "safety fund" of the health score (global view) uses it.

## "Invested this month" (budget)
`investissements_du_mois` (global view) = non-transfer outflows categorised `Investissement`/`Epargne` **+ deposits linked to an internal transfer** (`utils.budget_versement_ids`). A deposit with no linked transfer (repatriation of a contract, opening balance, profit-sharing) is not money taken from income: it is excluded, including from the virtual "Investissement" category (`expenses-by-category`, `budget-alerts`). `depenses_reelles` only subtracts categorised outflows, never deposits (absent from `depenses`). Per-account view unchanged (deposits there are the account's flows).

## Yearly review (`/wrapped`, `services/analytics/wrapped.py`)
Sum of the official monthly figures (`compute_budget`, `expenses_by_category`, `top_merchants`) to stay identical to the Dashboard. Current year = January → current month, compared with N-1 over the same period (`previous`, only if N-1 has transactions). Yearly savings rate = (income − real expenses) ÷ income; starting net worth = `patrimoine_net_total` of December N-1. Items: excluding Investissement/Epargne. Subscriptions: `Sortie` recurrences without `transfer_to_account_id` nor savings/investment category; cost = actual due dates of the year (net amount). Working hours at the current hourly rate (not historical).

## External services

Frankfurter (rates), Yahoo Finance (security search/quotes, ETF profiles). Only if the user makes use of them: ntfy / Telegram (notifications), Google's favicon service (logo of a domain), a private GitHub repository (encrypted backups); on the browser side, the world map's base layer comes from `unpkg.com`. No other outbound call, no telemetry (reference list: `ARCHITECTURE.md`).

## Reference

`ARCHITECTURE.md` (data model and routes), `backend/CLAUDE.md`, `frontend/src/CLAUDE.md`, skills `numera-backend`, `numera-frontend`, `numera-testing`.
