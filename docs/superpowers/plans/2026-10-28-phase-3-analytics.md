# Phase 3 — Analytics : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sortir tous les calculs d'indicateurs (budget, Centre d'Actions, métriques, rapports, insights, abonnements, bilan annuel, investissements et projections) des controllers vers `services/analytics/`, `repositories/analytics/` et `domain/`, avec **zéro écart de chiffres**, et faire passer chaque fichier et chaque fonction touchés sous les plafonds de taille.

**Architecture:** Une tâche 1 fige la sortie JSON de chaque route analytics sur un jeu de données déterministe (instantanés « golden master », date figée). Chaque tâche suivante découpe un domaine selon la recette, et le test d'instantanés doit rester identique **à l'octet près**. C'est le seul moyen fiable de déplacer des fonctions de 200 à 500 lignes de calcul sans changer un KPI.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic v2, pytest (Python 3.11), `freezegun` (nouvelle dépendance de développement, tâche 1).

**Spec:** `docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md` · plan maître : `docs/superpowers/plans/2026-10-28-architecture-en-couches.md` · plan de la phase précédente (modèle de rédaction et d'exécution) : `docs/superpowers/plans/2026-10-28-phase-2-domaines-ecriture.md`.

---

## 0. Reprendre ce plan dans une nouvelle conversation

### Message à coller pour démarrer

```text
On reprend la migration de Numera vers une architecture en couches. La phase 2 est terminée.
Lis d'abord, dans cet ordre : docs/superpowers/plans/2026-10-28-phase-3-analytics.md (en entier,
surtout la section 0), puis la spec docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md,
puis ARCHITECTURE.md § « Couches backend » et backend/CLAUDE.md.
Exécute la phase 3 toi-même dans cette session (skill superpowers:executing-plans), tâche par tâche,
en commençant par la tâche 1. Commits directement sur main.
```

### À lire avant de toucher au code

| Fichier | Pourquoi |
|---|---|
| ce plan, section 0 en entier | état du dépôt, conventions, pièges déjà rencontrés |
| `docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md` | règles des couches, plafonds, garde-fous (la référence en cas de doute) |
| `ARCHITECTURE.md` § « Couches backend » | table des couches et des erreurs métier telle qu'appliquée |
| `backend/CLAUDE.md` | conventions backend (erreurs, finance, tests) |
| skills `numera-backend`, `numera-expert`, `numera-testing` | procédures et règles métier (KPI, revenu, NET_AMOUNT, résilience…) |
| `docs/ACTION_CENTER.md` | règles du Centre d'Actions (tâche 4) |
| `.claude/skills/numera-expert/SKILL.md` § analytics | définitions exactes des KPI (ne pas les « corriger » pendant la migration) |

### Conventions de l'utilisateur (à respecter sans redemander)

- Échanges en français, concis. Commits **directement sur `main`**, sans branche ni PR, un commit par tâche, message en français terminé par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Ne jamais pousser.
- Exécution « native » : l'agent exécute lui-même (skill `superpowers:executing-plans`), sans sous-agent sauf demande explicite ; relecture finale faite par l'agent, signalée comme telle.
- Suivi : un ledger `.superpowers/sdd/2026-10-28-phase-3-analytics/progress.md` (créé par `…/skills/subagent-driven-development/scripts/sdd-workspace <plan>`), une ligne `Task N: complete` par tâche via `…/skills/executing-plans/scripts/task-done`, et une ligne `Task N: Ruling: <décision> — <pourquoi> — <coût si faux>` pour chaque écart au plan. Le ledger est relu en cas de reprise : une tâche marquée `complete` n'est pas refaite.
- Code : même style que l'existant (docstrings et commentaires en français, typage des signatures, pas de commentaires superflus).

### État du dépôt au début de la phase 3 (commit `e4436dc`)

- Couches en place : `backend/app/controllers/` (routers, ex-`api/`), `services/`, `repositories/`, `domain/`, `integrations/`, `core/`. Modèle de référence : `accounts`, et tous les routers d'écriture de la phase 2 (`categories`, `transactions`, `imports`, `salary`…).
- Erreurs métier (`app/core/errors.py`) traduites par `main.py` avec le même corps JSON qu'avant : `NotFoundError` 404, `InvalidOperationError` 400, `BusinessRuleError` 422, `ConflictError` 409, `InternalError` 500, `ExternalServiceError` 502, `ExternalTimeoutError` 504. `code=` + `context=` reproduisent l'ancien `api_error`.
- Déjà extrait en phase 1 (corps déplacés **tels quels**, à découper ici) : `services/analytics/budget.py` (`compute_budget` 506 lignes, `compute_budget_alerts` 133, `compute_resilience`), `services/analytics/cashflow.py` (`compute_cashflow_projection` 171), `services/audit.py` (`compute_action_center` 456 + helpers), `services/tax.py`. Requêtes partagées : `repositories/analytics/common.py` (`NET_AMOUNT`, `income_criterion`, `category_lines`, `budget_versement_ids`, `opening_balances_eur`, `savings_*`, `ticket_restaurant_account_ids`). Calculs purs : `domain/transactions.py` (`net_amount`, `tx_sample`, `tx_read`).
- Garde-fous actifs (aucun à désactiver) :
  - `backend/tests/test_architecture.py` + `architecture_baseline.txt` (**vide**, doit le rester) : règles d'import entre couches, imports locaux compris, import vers un module `app.*` introuvable, `commit()` dans `repositories/`.
  - `scripts/check_code_size.py` + `scripts/code_size_baseline.json` (63 entrées) : 400 lignes par fichier Python, 80 par fonction. Une entrée ne peut que diminuer ; repassée sous le plafond, elle **doit** être retirée (sinon `test_repository_matches_baseline` échoue). `make check-size`.
  - `backend/tests/conftest.py` : fixture `block_network` (autouse) — tout appel `httpx` réel lève `RuntimeError("Réseau interdit en test…")`.
- Suite : `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q` → **841 tests, ~100 s**. Importer l'app hors pytest exige `APP_ENV=test` (`APP_ENV=test PYTHONPATH=. python3.11 -c "import app.main"`).

### Pièges déjà rencontrés (phases 1-2) — à vérifier à chaque tâche

1. **Import relatif déplacé tel quel** (`from .subscriptions import x` copié dans `services/`) : il vise un module inexistant, et l'erreur est avalée par un `try/except` de règle d'audit → des actions disparaissent sans bruit. Le test d'architecture le signale (« introuvable ») : ne jamais l'ignorer.
2. **Renommage global par regex** (`budget_analytics(` → `compute_budget(`) qui renomme aussi la **définition** de la route → la route s'appelle elle-même en boucle. Après tout renommage : `grep -n "^async def compute_\|^def compute_" backend/app/controllers -r` → aucun résultat.
3. **Patch de test devenu sans effet** : un test qui fait `monkeypatch.setattr(<ancien module>, "get_market_quotes"/"get_exchange_rates"/"portfolio_overview", …)` n'agit plus quand le code appelant change de module. Le blocage réseau le fait échouer bruyamment ; corriger le **test** pour patcher le nouveau module. Cibles connues pour cette phase : `tests/test_month_review.py` (`budget_mod` = `app.services.analytics.budget`), `tests/test_wealth_forecast.py:137-146` (`app.controllers.analytics.portfolio.portfolio_overview`, appelé par la prévision de patrimoine).
4. **Nom de fonction devenu public qui masque une variable locale** (`savings_account_ids = savings_account_ids(db)` → `UnboundLocalError`). Après tout renommage, chercher `<nom> = <nom>(`.
5. **Liaison à l'import vs attribut de module** : si l'original faisait `from app.integrations.currency import convert_amount` *dans* la fonction, ou si des tests patchent le module, appeler `currency_module.convert_amount(...)` (attribut) pour garder l'effet des patchs.
6. **`sed` BSD (macOS)** : pas de `\b`, et `-i ''` obligatoire. Préférer un petit script Python pour les remplacements multi-lignes ou ciblés. Attention aux chaînes de **tests synthétiques** (`tests/test_architecture.py` écrit de faux modules `app/core/...`) qu'un remplacement global modifierait.
7. **Ordre et égalités** : garder exactement les tris (`order_by`, `sort(key=…)`) et l'ordre des sections ; une règle « première correspondance » dépend de l'ordre des lignes. Le test d'instantanés de la tâche 1 attrape ces écarts.
8. **Suite complète en arrière-plan** pendant qu'on édite → résultat non fiable. Lancer la suite au premier plan avec un délai long (`timeout` 400 000 ms), sortie redirigée dans le ledger (`… > .superpowers/sdd/…/tN-suite.log 2>&1; tail -1 …`).
9. **Exceptions larges** : `compute_budget` et `compute_action_center` enveloppent tout dans `try/except Exception` → `InternalError`. Une `DomainError` levée à l'intérieur doit être relancée telle quelle (`except DomainError: raise`), sinon un 404 devient 500.

### Correspondance des erreurs (inchangée)

| Aujourd'hui | Dans un service |
|---|---|
| 404 / `api_error(404, code, …)` | `NotFoundError(detail[, code, context])` |
| 400 | `InvalidOperationError` |
| 409 | `ConflictError` |
| 422 | `BusinessRuleError` |
| 500 | `InternalError` |
| 401, 403, 413, 429 | restent dans `controllers/` |

---

## Périmètre

| Dans la phase 3 | Reporté en phase 4 (portefeuille) |
|---|---|
| Controllers `analytics/budget`, `analytics/audit`, `analytics/metrics`, `analytics/reports`, `analytics/insights`, `analytics/subscriptions`, `analytics/wrapped`, `analytics/investments`, `tax` | Controllers `analytics/portfolio`, `analytics/dividends`, `analytics/diversity`, `holdings`, `investment_transactions`, `etf_profiles`, `market` |
| Services déjà extraits à découper : `services/analytics/budget.py`, `services/analytics/cashflow.py`, `services/audit.py` | `core/portfolio.py`, `core/holdings.py`, `core/dividends.py`, `core/market_data.py`, `core/etf_analyzer.py`, `core/seeds_etf.py` |
| `core/wealth.py`, `core/budget_period.py`, `core/subscription_prices.py`, `core/tax.py`, `core/tax_rules.py` | |

Les services d'investissement de la phase 3 (`services/analytics/investments/`) **appellent** `core/portfolio`, `core/holdings`, `core/market_data` tels quels ; ces modules ne bougent qu'en phase 4.

## Global Constraints

- **Zéro écart de chiffres** : `tests/test_analytics_snapshots.py` (tâche 1) passe à l'identique après chaque tâche. Un instantané ne se régénère **jamais** après la tâche 1 ; un écart est un bug à corriger, sauf ruling explicite dans le ledger (aucun n'est attendu).
- Mêmes routes, paramètres, codes et corps de réponse ; MCP (`mcp-server/server_api.py`) et frontend inchangés.
- `main` vert après chaque tâche : suite complète, `make check-size`, `tests/architecture_baseline.txt` vide.
- Fin de tâche : toute entrée de `scripts/code_size_baseline.json` des fichiers touchés a **disparu** (fichiers < 400 lignes, fonctions < 80). Un fichier qui dépasserait 400 lignes devient un package.
- Code déplacé : supprimé de l'ancien emplacement, sans ré-export (sauf `__init__.py` d'un package qui expose son API publique), tous les importeurs mis à jour (absolus, relatifs, locaux, tests, patchs). Module `core/` déplacé : `git mv` puis édition.
- Les définitions métier ne changent pas pendant la migration (revenu = `income_criterion`, KPI nets via `NET_AMOUNT`, dépenses réelles hors virements et hors Investissement/Epargne, patrimoine via `account_values`). Toute « anomalie » repérée va dans le ledger comme `minor (deferred)`, pas dans le code.
- Docs mises à jour dans le commit de la tâche quand un emplacement cité change (`ARCHITECTURE.md`, `CLAUDE.md`, `backend/CLAUDE.md`, skills, `docs/ACTION_CENTER.md`).

### Recette analytics (tâches 3 à 9)

1. **Repository** `repositories/analytics/<domaine>.py` : les requêtes d'agrégat (une fonction par requête nommée par son intention : `income_by_currency(db, start, end, account_id, tr_accounts)`…), sans `commit`.
2. **Domaine** `domain/<domaine>.py` : les formules pures (conversions EUR à partir de lignes déjà chargées, taux, ratios, séries, projections), testées sans base.
3. **Service** `services/analytics/<domaine>.py` — ou package `services/analytics/<domaine>/` si > 400 lignes — : une fonction publique par route, **nom `compute_<route>`** ou nom de la fonction de route actuelle quand il n'y a pas d'ambiguïté, signature `(db, <paramètres de la route hors db>)` ; orchestration en étapes < 80 lignes.
4. **Controller** : signature `Query` inchangée + `return await service.<fonction>(db, …)`. Aucun `db.query`, `commit` ni import de `app.models`.
5. Vérifier : instantanés identiques, suite complète, `make check-size`, entrées de baseline retirées, `grep -nE "db\.(query|add|commit|get)|from app\.models" backend/app/controllers/analytics/<fichier>.py` vide.

## Review Focus

- **Dérive silencieuse d'un KPI** (somme, arrondi, devise, ordre) : couverte par les instantanés ; ne jamais arrondir plus tôt ou plus tard qu'avant (les `round(…, 2)` restent au même endroit du calcul).
- **Dates relatives à « aujourd'hui »** (`datetime.now()`, `date.today()` dans projections, insights, cashflow, résilience) : les instantanés figent le temps avec `freezegun` ; un module qui importe `datetime` différemment (`from datetime import datetime` vs `import datetime`) doit rester couvert — vérifier qu'aucun instantané ne change d'un jour à l'autre (relancer le test deux fois avec deux dates système différentes n'est pas possible ; s'assurer que **toutes** les routes à date relative sont dans la liste de la tâche 1).
- **Centre d'Actions** : chaque règle est isolée dans un `try/except` qui l'empêche de casser l'ensemble ; un import cassé dans une règle la fait disparaître sans erreur. Les instantanés doivent contenir au moins une action de chaque type (sinon la tâche 1 complète le jeu de données).
- **Patrimoine et valorisation** : `core/wealth.account_values` est la source unique ; `compute_budget` (vue globale) et les routes investissements doivent continuer à l'appeler, pas à recalculer.
- **Exceptions larges** (piège 9).

---

### Task 1 : Instantanés de toutes les routes analytics (filet de sécurité)

**Files:**
- Modify: `backend/requirements-dev.txt` (ajouter `freezegun==1.5.1`) ; installer : `python3.11 -m pip install freezegun==1.5.1`
- Create: `backend/tests/test_analytics_snapshots.py`, `backend/tests/snapshots/analytics/*.json`

**Interfaces:**
- Fixture `snapshot_client` (module de test) : base de test (`db_session`/`client` de `conftest.py`), temps figé au **2026-06-15 10:00:00** (`freezegun.freeze_time`, `tick=False`), données = `await generate_demo_data(db, today=date(2026, 6, 15))` (`app.services.demo`, déterministe), plus les compléments nécessaires pour qu'au moins une action de chaque type du Centre d'Actions existe (transaction non catégorisée, doublon, virement non apparié, remboursement non affecté, hausse de prix d'abonnement, salaire configuré sans mois renseigné, budget dépassé…).
- Si une route tente le réseau (Yahoo, Frankfurter) : remplacer l'appel dans la fixture comme le font `tests/test_portfolio.py` (`market_data._fetch_chart`, `currency_mod.get_historical_rate`) et `tests/test_holdings_rebuild.py` — jamais en désactivant `block_network`.
- `ROUTES: list[tuple[str, str, dict]]` = (nom de fichier, chemin, paramètres). Au minimum, pour `month=5, year=2026` (mois complet) **et** `month=6, year=2026` (mois en cours) quand la route accepte un mois, et pour le compte courant de la démo quand elle accepte `account_id` :
  `/analytics/budget`, `/analytics/budget` (sans mois), `/analytics/resilience`, `/analytics/budget-alerts`, `/analytics/budget-period`, `/analytics/audit`, `/analytics/audit/{issue_id}` (pour chaque `issue_id` renvoyé par `/analytics/audit`), `/analytics/actions`, `/analytics/tags`, `/analytics/expenses-by-category`, `/analytics/top-merchants`, `/analytics/account-flow-summary`, `/analytics/kpi-history` (`months_count=12`), `/analytics/timeseries` (`year=2026` et `2025`), `/analytics/calendar`, `/analytics/cashflow-projection` (`days=30` et `90`), `/analytics/monthly-report`, `/analytics/money-flow`, `/analytics/sankey`, `/analytics/insights`, `/analytics/subscriptions` (avec et sans `include_other`), `/analytics/wrapped` (`year=2025` et `2026`), `/analytics/investments`, `/analytics/investments/{id}` et `/performance-history` (PEA et assurance-vie de la démo), `/analytics/investments-allocation`, `/analytics/investments-allocation-advanced`, `/analytics/patrimoine-allocation`, `/analytics/wealth-forecast` (défauts + un jeu de paramètres), `/analytics/fire`, `/analytics/asset-allocation/suggestions`, `/analytics/wealth-simulation` (défauts + `volatility_pct`, `tax_deferred`, un événement), `/tax/overview`, `/tax/annual-report?year=2025`, `/month-review?year=2026&month=5`.
- `_normalize(obj)` : arrondit tout `float` à 6 décimales, trie les clés ; ne trie **pas** les listes (l'ordre fait partie du contrat).
- Régénération : `UPDATE_SNAPSHOTS=1 PYTHONPATH=. python3.11 -m pytest tests/test_analytics_snapshots.py` écrit les fichiers ; sans la variable, le test compare et affiche le premier chemin JSON qui diffère.

- [ ] **Step 1 : Écrire le test et la fixture**, générer les instantanés sur le code actuel (`UPDATE_SNAPSHOTS=1`), relire 3 instantanés à la main (budget de mai, actions, wealth-forecast) : chiffres plausibles, aucune erreur 500, au moins une action de chaque type dans `actions.json`. Compléter les données sinon.
- [ ] **Step 2 : Stabilité** : relancer deux fois sans `UPDATE_SNAPSHOTS` → PASS ; lancer la suite complète → verte (le test n'en perturbe aucun autre).
- [ ] **Step 3 : Preuve que le filet attrape** : modifier temporairement un arrondi dans `compute_budget` (`round(x, 2)` → `round(x, 1)`) → le test échoue sur `budget_*.json` ; annuler la modification. Consigner dans le ledger.
- [ ] **Step 4 : Commit** — `test: instantanés de toutes les routes analytics (date figée, données de démo)`

### Task 2 : Modules `core/` restants du périmètre

**Files:** `git mv backend/app/core/wealth.py backend/app/services/wealth.py` ; `git mv backend/app/core/budget_period.py backend/app/services/budget_period.py` ; `git mv backend/app/core/subscription_prices.py backend/app/services/subscription_prices.py` ; `git mv backend/app/core/tax.py backend/app/domain/tax.py` ; `git mv backend/app/core/tax_rules.py backend/app/domain/tax_rules.py` ; importeurs (`grep -rlE "app\.core\.(wealth|budget_period|subscription_prices|tax|tax_rules)|from app\.core import (wealth|budget_period|subscription_prices|tax|tax_rules)" backend`) ; docs.

**Interfaces:**
- `domain/tax.py`, `domain/tax_rules.py` : noms publics inchangés ; vérifiés purs (n'importent que la bibliothèque standard et `tax_rules`) : `core/tax.py` importera `app.domain.tax_rules`.
- `services/budget_period.py` : noms publics inchangés (`period_bounds`, `current_period`, `describe`, `set_mode`, et le `ContextVar` de mode s'il est importé ailleurs) ; la partie calendaire pure (bornes d'un mois civil ou d'un mois de paie à partir d'une date de paie) va dans `domain/budget_period.py` si elle existe sans `Session`.
- `detect_price_changes` (85 lignes) < 80 : extraire la détection d'une série (`_series_change(…)`) en fonction pure dans `domain/subscription_prices.py`.
- `repositories/transactions.py` importe `period_bounds` : il importe désormais `services.budget_period` → **interdit** (repository → service). Déplacer l'appel : le service des transactions calcule les bornes et les passe au repository (`TransactionFilters` reçoit `period_start`/`period_end` résolus, ou le repository reçoit une fonction de bornes). Ruling attendu.

- [ ] **Step 1 : Test** : `test_domain_tax_rules_are_pure` n'est pas nécessaire (le test d'architecture le garantit) ; écrire `tests/test_domain_subscription_prices.py::test_series_change_detects_increase` (série 13,49 ×3 puis 15,99 → hausse de 2,50) → FAIL (module absent).
- [ ] **Step 2 : Déplacer, mettre à jour les importeurs, corriger la dépendance repository → service.**
- [ ] **Step 3 : Vérifier** — instantanés identiques ; suite complète ; architecture vide ; `core/subscription_prices.py::detect_price_changes` absente de la baseline ; `ls backend/app/core` = transverse + modules de la phase 4.
- [ ] **Step 4 : Commit** — `refactor: wealth, période budgétaire, abonnements et fiscalité hors de core/`

### Task 3 : Budget

**Files:** `services/analytics/budget.py` → package `services/analytics/budget/` (`__init__.py` exporte `compute_budget`, `compute_budget_alerts`, `compute_resilience`, `RESILIENCE_WINDOW_MONTHS`, `INVESTMENT_ACCOUNT_TYPES`) ; Create `repositories/analytics/budget.py`, `domain/budget.py`, `tests/test_domain_budget.py` ; Modify `controllers/analytics/budget.py`, `tests/test_month_review.py` (patch `budget_mod`).

**Interfaces:**
- `compute_budget(db, month, year, account_id) -> dict` découpée par les sections existantes (commentaires dans le code), chaque étape < 80 lignes :
  `_income(…)` (entrées + dividendes + versements en vue compte), `_interests(…)`, `_expenses(…)` (dont retraits en vue compte), `_investments(…)` (catégories Investissement/Epargne + versements alimentés par le budget), `_savings_rate(…)`, `_wealth(…)` (valorisation des comptes investissement, soldes courant/épargne, vue globale via `account_values`), `_account_view(…)` (recalcul en devise du compte quand `account_id`). Les requêtes de chaque section → `repositories/analytics/budget.py` ; les conversions EUR et ratios purs → `domain/budget.py` (`to_eur(rows_by_currency, rates) -> float`, `savings_rate(revenus, depenses_reelles) -> float`, …).
- `compute_budget_alerts` (133) découpée : requêtes de dépenses mensuelles/annuelles par catégorie → repository ; construction d'une `BudgetAlert` → domaine (`budget_alert(category, monthly_spent, annual_spent) -> BudgetAlert | None`).
- Le `try/except` global garde `except DomainError: raise` puis `except Exception` → `InternalError("Erreur interne lors du calcul du budget")`.

- [ ] **Step 1 : Tests de domaine** (`tests/test_domain_budget.py`) : `test_to_eur_sums_per_currency` (`{"EUR": 100, "USD": 108}` avec `USD=1.08` → 200.0) ; `test_savings_rate_zero_income_is_zero` ; un test par fonction pure extraite → FAIL.
- [ ] **Step 2 : Découper.**
- [ ] **Step 3 : Vérifier** (recette, étape 5) ; entrées `services/analytics/budget.py*` absentes de la baseline.
- [ ] **Step 4 : Commit** — `refactor(analytics): budget découpé (repository, domaine, étapes)`

### Task 4 : Centre d'Actions et audit des données

**Files:** `services/audit.py` → package `services/audit/` : `__init__.py` (`compute_action_center`, `merchant_key`, `month_name`, `unallocated_reimbursements_query`), `context.py`, `rules/<règle>.py`, `data_audit.py` ; Create `repositories/analytics/audit.py` ; Modify `controllers/analytics/audit.py` (`data_audit` 285 lignes, `data_audit_issue_details` 126, `dismiss_action`), `services/notifications.py` (importe `compute_action_center`), `docs/ACTION_CENTER.md`.

**Interfaces:**
- `AuditContext` (dataclass, `context.py`) : `db`, `now`, `rates`, `dismissed: set[str]`, et les données partagées par plusieurs règles (chargées une fois).
- Une règle = un module `rules/<nom>.py` exposant `def detect(ctx: AuditContext) -> list[ActionItem]` (ou `async def` si elle attend un taux/cours). Règles, **dans cet ordre** (celui du code actuel) : `uncategorized`, `duplicates`, `missing_snapshots`, `missing_salary`, `unmatched_transfers`, `unallocated_reimbursements`, `budget`, `rule_suggestions`, `merchant_suggestions`, `dividends`, `broker_reconciliation`, `subscription_prices`, `backups`.
- `RULES: list` dans `__init__.py` ; `compute_action_center(db)` construit le contexte, exécute chaque règle dans son `try/except` (comportement actuel : une règle en échec est journalisée et ignorée), puis la section « Summary & Sort » existante.
- `data_audit` et `data_audit_issue_details` → `services/audit/data_audit.py` (`compute_data_audit(db) -> DataAuditResponse`, `compute_data_audit_issue(db, issue_id)` qui lève `NotFoundError("Audit issue not found or not editable")`) ; elles réutilisent les mêmes requêtes que les règles via `repositories/analytics/audit.py`.
- `dismiss_action` → service (`dismiss_action(db, action_id) -> dict`).

- [ ] **Step 1 : Test** : `tests/test_audit_rules.py::test_rules_registry_order` (les noms de `RULES` dans l'ordre ci-dessus) et `test_failing_rule_does_not_break_action_center` (une règle factice qui lève, ajoutée par `monkeypatch` à `RULES` → `compute_action_center` renvoie les autres actions) → FAIL.
- [ ] **Step 2 : Découper** (une règle à la fois ; lancer `tests/test_analytics_snapshots.py -k actions` après chaque règle).
- [ ] **Step 3 : Vérifier** ; `docs/ACTION_CENTER.md` § « Ajouter une action » : « créer `services/audit/rules/<nom>.py` avec `detect(ctx)`, l'ajouter à `RULES` » ; skill `numera-backend` § Centre d'Actions mis à jour.
- [ ] **Step 4 : Commit** — `refactor(audit): Centre d'Actions en registre de règles, audit des données dans services/`

### Task 5 : Métriques

**Files:** Create package `services/analytics/metrics/` (`tags.py`, `categories.py` (expenses-by-category, top-merchants), `account_flow.py`, `kpi_history.py`, `timeseries.py`, `calendar.py`), `repositories/analytics/metrics.py`, `domain/metrics.py` si des calculs purs se dégagent ; Modify `controllers/analytics/metrics.py` (983 lignes).

**Interfaces:** une fonction de service par route : `compute_tags(db, month, year, start_date, end_date, account_id)`, `compute_expenses_by_category(db, month, year, account_id)`, `compute_top_merchants(db, month, year, limit, account_id)`, `compute_account_flow_summary(db, account_id, start_date, end_date)`, `compute_kpi_history(db, months_count, account_id)` (203 lignes → étapes : bornes des mois, revenus, dépenses, épargne, patrimoine), `compute_timeseries(db, year, account_id)` (162), `compute_calendar(db, month, year, account_id)` (244 → événements passés, récurrences à venir, agrégats par jour). Chaque fonction < 80 lignes.

- [ ] **Step 1 : Tests** : pour chaque calcul pur extrait (par ex. agrégation par jour du calendrier, cumul du kpi-history), un test sur des données en mémoire → FAIL.
- [ ] **Step 2 : Découper** (une route à la fois, instantanés après chacune).
- [ ] **Step 3 : Vérifier** ; `controllers/analytics/metrics.py` et ses 4 fonctions absents de la baseline.
- [ ] **Step 4 : Commit** — `refactor(analytics): métriques dans services/analytics/metrics`

### Task 6 : Rapports, flux d'argent, Sankey, projection de trésorerie

**Files:** Create package `services/analytics/reports/` (`monthly_report.py`, `money_flow.py`, `sankey.py`) ; déplacer `services/analytics/cashflow.py` dans ce package (`cashflow.py`) ; `repositories/analytics/reports.py` ; `domain/reports.py` (`calc_diff` y va : `tests/test_import_and_analytics.py` l'importe) ; Modify `controllers/analytics/reports.py`, `services/notifications.py`, `services/month_review.py` (importent `compute_cashflow_projection` / helpers).

**Interfaces:** `compute_monthly_report(db, month, year, account_id)` (97), `compute_money_flow(db, month, year, account_id)` et son helper `_calculate_money_flow_data` (103), `compute_sankey(db, month, year, account_id)` (221 → nœuds, liens revenus, liens dépenses par catégorie via `category_lines`, épargne), `compute_cashflow_projection` (171 → solde actuel, échéances récurrentes, série journalière) ; chacune < 80 lignes.

- [ ] **Step 1 : Tests** : `tests/test_domain_reports.py::test_calc_diff_with_negative_values` (reprend le cas de `test_import_and_analytics.py`) et un test par fonction pure extraite (construction des liens Sankey à partir de totaux) → FAIL.
- [ ] **Step 2 : Découper.**
- [ ] **Step 3 : Vérifier** ; entrées `controllers/analytics/reports.py*` et `services/analytics/cashflow.py*` absentes de la baseline.
- [ ] **Step 4 : Commit** — `refactor(analytics): rapports, money-flow, Sankey et trésorerie dans services/analytics/reports`

### Task 7 : Insights, abonnements, bilan annuel

**Files:** Create `services/analytics/insights.py`, `services/analytics/subscriptions.py`, package `services/analytics/wrapped/` si > 400 lignes (sinon `wrapped.py`), `repositories/analytics/{insights,subscriptions,wrapped}.py` ; Modify `controllers/analytics/{insights,subscriptions,wrapped}.py`.

**Interfaces:**
- `compute_insights(db, month, year, account_id)` (199 → score de santé, insights par thème), `dismiss_insight(db, title)`.
- `compute_subscriptions(db, account_id, include_other)` (108), `ignore_subscription_detection(db, data)`, `price_change_read` (dans le service), `get_subscription_total_for_period` (appelé par `controllers/analytics/insights.py:51` via un **import relatif** `from .subscriptions import …` → piège n° 1 : le service des insights l'importe depuis `services.analytics.subscriptions`).
- `compute_wrapped(db, year)` : les helpers privés actuels (`_totals` 61, `_build_wrapped` 55, `_subscription_changes`…) deviennent des étapes du service ; `_period`, `_pct_change`, `_hours` purs → `domain/wrapped.py`.
- `load_work_time` (`services/work_time.py`) reste la source du taux horaire.

- [ ] **Step 1 : Tests** : `tests/test_domain_wrapped.py::test_pct_change` (0 → None ou valeur actuelle, à lire dans `_pct_change`) ; un test par autre fonction pure → FAIL.
- [ ] **Step 2 : Découper.**
- [ ] **Step 3 : Vérifier** ; entrées `insights.py::get_intelligent_insights`, `subscriptions.py::get_subscriptions_analytics` absentes de la baseline.
- [ ] **Step 4 : Commit** — `refactor(analytics): insights, abonnements et bilan annuel dans services/`

### Task 8 : Investissements et projections

**Files:** Create package `services/analytics/investments/` (`summary.py` : `/investments`, `_calculate_investment_flows` ; `account.py` : `/investments/{id}` et `/performance-history` ; `allocation.py` : `/investments-allocation`, `-advanced`, `/patrimoine-allocation`, `/asset-allocation/suggestions` ; `projections.py` : `/wealth-forecast`, `/fire`, `/wealth-simulation`), `domain/projections.py`, `tests/test_domain_projections.py` ; Modify `controllers/analytics/investments.py` (1 371 lignes), `tests/test_wealth_forecast.py` (patch de `portfolio_overview` : viser le module qui l'appelle désormais).

**Interfaces:**
- `domain/projections.py` (pur, sans base) : `months_to_target(...)` (ex-`_months_to_target`), simulation de patrimoine année par année (`simulate_wealth(initial_capital, monthly_contribution, annual_return_pct, years, volatility_pct, inflation_rate_pct, contribution_indexation_pct, tax_rate_pct, tax_deferred, events) -> list[WealthSimulationPoint]` ou équivalent), projection FIRE (`fire_projection(...)`), courbe de prévision (`wealth_forecast_series(...)`). Les signatures exactes suivent les paramètres actuels des routes.
- Services : une fonction par route (`compute_investments`, `compute_investment_account`, `compute_performance_history`, `compute_allocation`, `compute_allocation_advanced`, `compute_patrimoine_allocation`, `compute_wealth_forecast`, `compute_fire`, `compute_allocation_suggestions`, `compute_wealth_simulation`), chacune < 80 lignes ; elles appellent `core/portfolio`, `services/wealth` sans les modifier.
- La route `/analytics/portfolio` (phase 4) reste dans `controllers/analytics/portfolio.py` ; `wealth_forecast` appelle `portfolio_overview` de ce controller par un import **local** (`controllers/analytics/investments.py:893`, `from .portfolio import portfolio_overview`) : faire appeler une fonction de **service** (créer `services/analytics/portfolio.py::portfolio_overview` en y déplaçant la logique de cette route, le controller l'appelant) — un service ne peut pas importer un controller.

- [ ] **Step 1 : Tests de domaine** : `test_months_to_target` (cas simples : objectif déjà atteint → 0 ; rendement nul → division exacte) ; `test_simulation_without_volatility_is_deterministic` ; `test_fire_target_is_expenses_over_withdrawal_rate` → FAIL.
- [ ] **Step 2 : Découper** (fichier par fichier, instantanés après chacun).
- [ ] **Step 3 : Vérifier** ; les 8 entrées `controllers/analytics/investments.py*` absentes de la baseline.
- [ ] **Step 4 : Commit** — `refactor(analytics): investissements et projections dans services/, simulations pures dans domain/`

### Task 9 : Fiscalité et budget-period (controllers restants)

**Files:** Modify `controllers/tax.py` (la logique de repli de `get_overview` — résilience indisponible → `None` — va dans `services/tax.py::tax_overview(db, today)`), `controllers/analytics/budget.py` (`get_budget_period`, `set_budget_period_mode` → `services/budget_period.py`).

- [ ] **Step 1 : Test** : `tests/test_tax_service.py::test_overview_survives_resilience_failure` (`monkeypatch` de `compute_resilience` qui lève → `precaution_months is None`, pas d'erreur) → FAIL.
- [ ] **Step 2 : Déplacer.**
- [ ] **Step 3 : Vérifier** ; aucun `try/except` ni calcul dans ces controllers.
- [ ] **Step 4 : Commit** — `refactor: fiscalité et période budgétaire appelées via services/`

### Task 10 : Clôture de la phase 3

**Files:** `ARCHITECTURE.md`, `CLAUDE.md`, `backend/CLAUDE.md`, skills `numera-backend` / `numera-expert` / `numera-testing`, `docs/ACTION_CENTER.md`, plan maître.

- [ ] **Step 1 : Périmètre** : `grep -nE "db\.(query|add|commit|get)|from app\.models" backend/app/controllers/analytics/{budget,audit,metrics,reports,insights,subscriptions,wrapped,investments}.py backend/app/controllers/tax.py` → vide ; `ls backend/app/core` = `config, errors, logging, login_events, login_rate_limit, mcp_tokens, migrations, security, time, totp` + modules de la phase 4.
- [ ] **Step 2 : Docs** : arborescence et § Couches de `ARCHITECTURE.md` ; tous les emplacements cités (`grep -rnE "core/(wealth|budget_period|subscription_prices|tax)|services/analytics/budget\.py|services/audit\.py|controllers/analytics/(metrics|reports|insights|wrapped|investments)\.py" --include=*.md` hors `docs/superpowers/`) ; skill `numera-testing` : décrire le test d'instantanés et la règle « ne jamais régénérer pour faire passer ». Nombre de tests mis à jour dans `CLAUDE.md` et `backend/CLAUDE.md`. Plan maître : phase 3 terminée ; écrire la section « Reprendre » de la phase 4 sur le modèle de la section 0 de ce plan.
- [ ] **Step 3 : Suite complète, `make check-size`, `cd frontend && npm run build`.**
- [ ] **Step 4 : Relecture finale** (Review Focus ci-dessus, point par point), rulings et `minor (deferred)` du ledger rapportés à l'utilisateur.
- [ ] **Step 5 : Commit** — `docs: phase 3 de la migration en couches terminée`
