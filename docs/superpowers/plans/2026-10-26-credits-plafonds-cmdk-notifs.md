# Crédits, plafonds, actions ⌘K, notifications — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter les crédits (patrimoine net), le LDDS/LEP + un conseil d'ordre de remplissage, des actions dans ⌘K et des notifications ntfy/Telegram.

**Architecture:** Calculs purs dans `backend/app/core/` (loans, notifications), routers fins dans `backend/app/api/`, branchement du patrimoine dans `core/wealth.py` (source unique), notifications dans la tâche horaire existante de `main.py`. Frontend : nouveaux composants par domaine, l'Omnibox existante est enrichie.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, httpx 0.27 ; React 18, TypeScript, Tailwind, shadcn/ui, Recharts.

**Spec:** `docs/superpowers/specs/2026-10-26-credits-plafonds-cmdk-notifs-design.md`

## Global Constraints

- Python 3.11/3.12 ; tests : `cd backend && PYTHONPATH=. python -m pytest tests -q` ; frontend : `cd frontend && npm run build`.
- Montants toujours positifs en base ; KPI calculés côté backend uniquement.
- Nouveau modèle → importé dans `app/models/__init__.py` ; nouvelle migration avec garde `has_table` (base créée par `create_all`), `down_revision` = tête courante (`f6b1d8e3a9c4` au départ).
- Nouveau router → importé dans `main.py` **et** ajouté à `protected_routers`.
- Routes de lecture nouvelles → reprises dans `mcp-server/server_api.py` ; aucun outil MCP d'écriture.
- `ARCHITECTURE.md` mis à jour dans le commit de chaque fonctionnalité. Commits directement sur `main`.
- Valeurs : LDDS 12 000 €, LEP 10 000 € ; IRA max = min(6 mois d'intérêts sur le montant remboursé, 3 % du CRD) ; ntfy par défaut `https://ntfy.sh` ; délai HTTP 10 s ; sévérité minimale par défaut `medium` ; résumé hebdo dimanche ≥ 18 h, une fois par semaine ISO.

## Review Focus

- Crédit à taux 0 % : mensualité = capital / durée, pas de division par zéro.
- Remboursement anticipé ≥ CRD : le prêt se termine à cette date (CRD 0), aucune ligne négative.
- Date `at` avant la première échéance ou après la dernière : CRD = capital, puis 0.
- Canal de notification en panne (timeout, 401) : la tâche horaire continue, rien n'est marqué envoyé.
- Saisie ⌘K `12,50` (virgule), `+1200`, `12.5€` : montant reconnu. Une requête comme `2025 bilan` propose aussi la saisie rapide, mais elle passe **après** les vues et comptes correspondants, et rien n'est enregistré sans le formulaire.

---

### Task 1: Calcul des prêts (`core/loans.py`)

**Files:**
- Create: `backend/app/core/loans.py`
- Test: `backend/tests/test_loans_core.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) LoanTerms(principal: float, annual_rate_pct: float, duration_months: int, start_date: date, insurance_monthly: float = 0.0)`
  - `@dataclass(frozen=True) Prepayment(date: date, amount: float, mode: Literal["reduce_duration", "reduce_payment"])`
  - `@dataclass(frozen=True) ScheduleRow(n: int, date: date, payment: float, interest: float, principal: float, insurance: float, remaining: float, prepayment: float = 0.0)`
  - `monthly_payment(principal: float, annual_rate_pct: float, months: int) -> float`
  - `build_schedule(terms: LoanTerms, prepayments: list[Prepayment] = []) -> list[ScheduleRow]` — échéance n à `start_date + (n-1) mois` ; un remboursement anticipé est appliqué après l'échéance dont la date est ≤ sa date ; `reduce_payment` recalcule la mensualité sur la durée restante, `reduce_duration` garde la mensualité.
  - `remaining_principal(terms, prepayments, at: date) -> float`
  - `simulate_prepayment(terms, prepayments, amount: float, at: date, mode) -> dict` clés `interest_saved`, `new_end_date`, `new_payment`, `months_saved`, `max_penalty`, `total_interest_before`, `total_interest_after`.

- [ ] **Step 1: Write the failing tests**
  - `test_monthly_payment_standard` : `monthly_payment(200_000, 3.6, 300) == pytest.approx(1012.00, abs=0.01)`.
  - `test_monthly_payment_zero_rate` : `monthly_payment(12_000, 0, 24) == 500.0`.
  - `test_schedule_ends_at_zero` : 300 lignes, `rows[-1].remaining == 0`, `sum(r.principal) == pytest.approx(200_000, abs=0.01)`.
  - `test_remaining_principal_bounds` : avant `start_date` → 200 000 ; après la dernière échéance → 0.
  - `test_prepayment_reduce_duration` : 20 000 au mois 60 → moins de 300 lignes, même mensualité.
  - `test_prepayment_reduce_payment` : même cas → 300 lignes, mensualité après < avant.
  - `test_prepayment_exceeding_remaining_closes_loan` : 1 000 000 → `rows[-1].remaining == 0`, aucune valeur négative.
  - `test_simulate_max_penalty` : `max_penalty == min(amount * rate/12 * 6, 0.03 * crd)`.

- [ ] **Step 2: Run** `PYTHONPATH=. python -m pytest tests/test_loans_core.py -v` → FAIL (module absent).
- [ ] **Step 3: Implement** les fonctions ci-dessus ; arrondi au centime par ligne, la dernière échéance solde le reste.
- [ ] **Step 4: Run** → PASS.

### Task 2: Modèles, migration, patrimoine et API des prêts

**Files:**
- Create: `backend/app/models/loan.py` (`Loan`, `LoanPrepayment`), `backend/alembic/versions/a7c2e9f4b1d3_loans.py`, `backend/app/schemas/loan.py`, `backend/app/api/loans.py`
- Modify: `backend/app/models/__init__.py`, `backend/app/schemas/account.py` (`AccountType` + `"credit"`), `backend/app/core/wealth.py`, `backend/app/api/accounts.py` (`balance` d'un compte crédit = `−CRD`), `backend/app/api/analytics/investments.py` (`patrimoine_allocation` : crédits hors items, champs `total_debts_eur`, `net_patrimoine_eur`), `backend/app/main.py`, `mcp-server/server_api.py`, `ARCHITECTURE.md`
- Test: `backend/tests/test_loans_api.py`

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `Loan`: `id, account_id (unique, FK accounts ondelete CASCADE), kind String(16), principal, annual_rate_pct, duration_months, start_date Date, insurance_monthly`; `LoanPrepayment`: `id, loan_id (FK CASCADE), date Date, amount, mode String(16)`.
  - `core/loans.py::terms_of(loan: Loan) -> tuple[LoanTerms, list[Prepayment]]`, `loan_remaining(db, account_id, at: date) -> float | None`.
  - Routes (`/loans`) : `GET ""` (liste avec résumé), `POST ""` (crée compte `credit` + prêt ; corps : `name, institution?, logo?, color?, kind, principal, annual_rate_pct, duration_months, start_date, insurance_monthly`), `GET /{loan_id}`, `PATCH /{loan_id}`, `DELETE /{loan_id}` (supprime aussi le compte), `GET /{loan_id}/schedule`, `POST /{loan_id}/simulate-prepayment` (`amount, date, mode`), `POST /{loan_id}/prepayments`, `DELETE /{loan_id}/prepayments/{id}`, `GET /by-account/{account_id}`.
  - `LoanSummary`: `id, account_id, name, kind, principal, annual_rate_pct, duration_months, start_date, insurance_monthly, monthly_payment, remaining_principal, repaid_pct, end_date, total_interest, total_cost, prepayments[]`.

- [ ] **Step 1: Write the failing tests**
  - `test_create_loan_creates_credit_account` : POST → 201 ; en base, un `Account(type="credit")` et un `Loan` liés.
  - `test_account_balance_is_negative_remaining` : `GET /accounts/{id}` → `balance == -remaining_principal`.
  - `test_wealth_counts_loan_negatively` : un courant à 10 000 + un prêt de 200 000 commencé il y a 12 mois → `account_values` du crédit < 0 et `/analytics/patrimoine-allocation` renvoie `net_patrimoine_eur == 10 000 − CRD`, aucun item de type `credit`.
  - `test_schedule_and_simulation_endpoints` : 300 lignes ; `interest_saved > 0`.
  - `test_prepayment_persists_and_changes_summary` : POST remboursement anticipé → `remaining_principal` diminue.
  - `test_delete_loan_deletes_account`.
  - `test_kpis_ignore_credit_account` : un prêt n'ajoute rien aux revenus/dépenses de `/analytics/summary`… (vérifier le total dépenses inchangé).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** modèles, migration (garde `has_table`), schémas, router, branchement `wealth.py` (avant le test `positions` : `if acc.type == "credit"` → `AccountValue(-crd, -crd/rate, "loan")`), solde de compte, allocation patrimoine, MCP (`list_loans`, `get_loan_schedule`).
- [ ] **Step 4: Run** test file puis suite complète → PASS.

### Task 3: UI crédits

**Files:**
- Create: `frontend/src/components/loans/LoanDialog.tsx` (création/édition), `frontend/src/components/loans/LoanView.tsx` (résumé, courbe CRD, tableau par année repliable, simulateur, remboursements anticipés)
- Modify: `frontend/src/pages/Accounts.tsx` (bouton « Ajouter un crédit », `?new=loan` l'ouvre), `frontend/src/pages/AccountDetail.tsx` (compte `credit` → rend `LoanView` à la place des onglets de transactions), `frontend/src/lib/labels.ts` (`credit` → « Crédit »), composant d'allocation du patrimoine (lignes Dettes / Patrimoine net si `total_debts_eur > 0`).

- [ ] **Step 1:** Implémenter ; montants via `formatCurrency` et mode confidentialité.
- [ ] **Step 2: Run** `cd frontend && npm run build` → succès.
- [ ] **Step 3:** Vérifier dans le navigateur : créer un crédit, voir le tableau, simuler, supprimer.
- [ ] **Step 4: Commit** tâches 1-3 : `feat: crédits et emprunts (échéancier, patrimoine net, remboursement anticipé)`.

### Task 4: LDDS, LEP et conseil d'ordre de remplissage

**Files:**
- Modify: `backend/app/core/tax_rules.py` (`ldds_ceiling`, `lep_ceiling` + sources), `backend/app/core/tax.py` (`ldds_status`, `lep_status`, motifs `_WRAPPER_PATTERNS`, `allocation_advice`), `backend/app/schemas/account.py` (`TaxWrapper` + `ldds`, `lep`), `backend/app/schemas/tax.py` (`AllocationAdvice`, champ `allocation_advice: list[AllocationAdvice]` dans `TaxOverview`), `backend/app/api/analytics/tax.py`, `frontend/src/pages/Tax.tsx`, sélecteur d'enveloppe du formulaire de compte, `ARCHITECTURE.md`
- Test: `backend/tests/test_tax_rules.py`, `backend/tests/test_tax_api.py`, `backend/tests/test_tax_wrapper_guess.py`

**Interfaces:**
- Produces: `allocation_advice(cards: list[dict], months_of_expenses: float | None, tmi_pct: float | None) -> list[dict]` ; chaque élément `{rank, kind, account_id, account_name, reason, remaining}`. `AllocationAdvice` Pydantic, mêmes champs.
- Ordre : (1) précaution < 3 mois → premier livret avec place parmi `lep, livret_a, ldds, livret_jeune` ; (2) 3–6 mois → idem ; (3) PEA avec place, ou `kind="pea", account_id=None` « ouvrir un PEA » ; (4) `tmi_pct >= 30` et PER avec place ; (5) assurance-vie absente → « ouvrir », sinon `cto`.

- [ ] **Step 1: Write the failing tests**
  - `test_ldds_lep_ceilings` : `rules_for(2026).ldds_ceiling == 12_000`, `.lep_ceiling == 10_000`.
  - `test_guess_ldds_lep` : « LDDS Boursorama » → `ldds` ; « Livret d'épargne populaire » → `lep`.
  - `test_advice_low_buffer_prefers_lep` : précaution 1 mois, LEP et Livret A avec place → rang 1 = `lep`.
  - `test_advice_no_pea_suggests_opening` : aucune carte PEA → un conseil `pea` avec `account_id is None`.
  - `test_advice_per_only_high_tmi` : TMI 11 → pas de `per` ; TMI 30 → `per` présent.
  - `test_overview_exposes_advice` (API) : `GET /tax/overview` contient `allocation_advice`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS ; `npm run build`.
- [ ] **Step 5: Commit** `feat(fiscalité): LDDS, LEP et conseil d'ordre de remplissage`.

### Task 5: Actions dans ⌘K

**Files:**
- Create: `frontend/src/lib/quickEntry.ts`
- Modify: `frontend/src/components/layout/Omnibox.tsx`, `frontend/src/pages/AccountDetail.tsx` (lit `?new=tx&type=&amount=&merchant=` pour ouvrir le formulaire pré-rempli puis nettoie l'URL ; `?tx=<id>` fait défiler et met en évidence la ligne), `frontend/src/pages/MonthReview.tsx` si besoin, `ARCHITECTURE.md`

**Interfaces:**
- Produces: `parseQuickEntry(query: string): { amount: number; type: "Sortie" | "Entree"; merchant: string } | null` — regex en tête `^([+-]?)\s*(\d+(?:[.,]\d{1,2})?)\s*€?(?:\s+(.+))?$` ; `+` → `Entree`, sinon `Sortie` ; montant > 0 obligatoire.
- Actions : Nouvelle transaction (compte principal), Importer un CSV (`/settings?tab=import`), Revue du mois (`/month/revue`), Mode confidentialité (`togglePrivacyMode`), Ajouter un crédit (`/accounts?new=loan`), Notification de test (`POST /notifications/test`, Task 6 ; action masquée tant que l'endpoint répond 404).

- [ ] **Step 1:** Implémenter `parseQuickEntry` et la section « Actions » + l'entrée de saisie rapide en tête des résultats.
- [ ] **Step 2: Run** `npm run build` → succès.
- [ ] **Step 3:** Vérifier dans le navigateur : `12,50 boulangerie` ouvre le formulaire pré-rempli sur le compte principal ; transaction trouvée → ligne mise en évidence.
- [ ] **Step 4: Commit** `feat(omnibox): saisie rapide et actions dans ⌘K`.

### Task 6: Notifications ntfy et Telegram

**Files:**
- Create: `backend/app/core/notifications.py`, `backend/app/models/notification_log.py`, `backend/alembic/versions/b8d3f1a6c2e4_notification_log.py`, `backend/app/api/notifications.py`, `backend/app/schemas/notification.py`, `frontend/src/components/settings/NotificationsSettings.tsx`
- Modify: `backend/app/models/__init__.py`, `backend/app/main.py` (router + appel `await run_notifications(db)` dans la tâche horaire), `frontend/src/pages/Settings.tsx` (onglet `notifications`), `ARCHITECTURE.md`, `docs/ACTION_CENTER.md`
- Test: `backend/tests/test_notifications.py`

**Interfaces:**
- Produces:
  - `NotificationLog`: `id, fingerprint String(64) unique, action_id String(120), channel String(16), sent_at DateTime`.
  - Réglages `system_settings` : `notify.ntfy.enabled`, `notify.ntfy.server`, `notify.ntfy.topic`, `notify.ntfy.token`, `notify.telegram.enabled`, `notify.telegram.bot_token`, `notify.telegram.chat_id`, `notify.min_severity`, `notify.weekly_digest`, `notify.hide_amounts`, `notify.public_url`, `notify.initialized`, `notify.last_digest_week`.
  - `class Channel(Protocol): name: str; async def send(self, title: str, body: str, priority: str = "default", url: str | None = None) -> None` ; `NtfyChannel(server, topic, token)` ; `TelegramChannel(bot_token, chat_id)` ; `enabled_channels(db) -> list[Channel]`.
  - `fingerprint(action: ActionItem) -> str` (sha256 de `id|title|description`) ; `mask_amounts(text: str) -> str` ; `async run_notifications(db, now: datetime | None = None) -> int` (nombre de messages envoyés) ; `async send_weekly_digest(db, now) -> bool`.
  - Routes `/notifications` : `GET /settings` (jetons masqués `••••` + 4 derniers caractères), `PUT /settings` (un jeton masqué renvoyé tel quel n'écrase pas la valeur), `POST /test` (`channel: "ntfy" | "telegram"`).
  - Sévérités : `low < medium < high`.

- [ ] **Step 1: Write the failing tests** (canaux remplacés par un faux `Channel` qui enregistre les envois, via `monkeypatch` de `enabled_channels`)
  - `test_first_run_sends_single_hello` : 3 actions existantes → 1 message, 3 lignes `notification_log`, `notify.initialized == "1"`.
  - `test_new_action_sent_once` : 2e passage avec une nouvelle action → 1 message ; 3e passage → 0.
  - `test_changed_action_resent` : description modifiée → renvoyée.
  - `test_min_severity_filters` : `min_severity=high` → une action `medium` n'est pas envoyée.
  - `test_failed_channel_not_logged` : le faux canal lève `httpx.TimeoutException` → aucune ligne de log, pas d'exception propagée.
  - `test_mask_amounts` : `"Budget 1 234,56 € dépassé"` → `"Budget ••• € dépassé"`.
  - `test_weekly_digest_once_per_week` : dimanche 19 h → envoyé ; second appel même semaine → non ; samedi → non.
  - `test_settings_masks_tokens` (API) : PUT token puis GET → `"••••abcd"` ; PUT avec la valeur masquée → token en base inchangé.
  - `test_ntfy_channel_request` : `httpx.MockTransport` vérifie URL `{server}/{topic}`, en-têtes `Title`, `Priority`, `Authorization`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (le calcul des actions réutilise `get_action_center(db)` ; actions ignorées déjà exclues par celui-ci ; le résumé réutilise les fonctions analytics existantes du budget et des récurrences). **Step 4: Run** → PASS, suite complète.
- [ ] **Step 5:** Onglet Paramètres « Notifications » + bouton test ; `npm run build` ; vérification navigateur.
- [ ] **Step 6: Commit** `feat: notifications push ntfy et Telegram`.

### Task 7: Vérification finale

- [ ] Suite backend complète verte, `npm run build` vert, `ARCHITECTURE.md` et skills (`numera-expert` : crédits, patrimoine net) à jour.
