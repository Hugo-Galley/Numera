# Phase 2 — Domaines d'écriture : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Renommer `api/` en `controllers/`, puis migrer les routers d'écriture côté budget (référentiels, transactions, import, récurrences, salaire, revue de mois, administration) vers `controllers → services → repositories / domain / integrations`, vider `core/` du métier qui leur appartient, et faire repasser tous ces fichiers et fonctions sous les plafonds.

**Architecture:** Même recette que `accounts` (phase 1) appliquée domaine par domaine, du plus simple au plus risqué. Les modules `core/` liés à un domaine sont déplacés (`git mv`) dans la tâche de ce domaine. La frontière de transaction de `recalculate_running_balances` (commit → flush) ne bouge qu'à la tâche 15, une fois tous ses appelants devenus des services.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic v2, pytest (Python 3.11).

**Spec:** `docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md` · plan maître : `docs/superpowers/plans/2026-10-28-architecture-en-couches.md` (phase 1 terminée, commits `143b483..aa5a887`).

## Périmètre

| Dans la phase 2 | Reporté |
|---|---|
| Routers `categories`, `tags`, `merchants`, `categorization_rules`, `transfer_rules`, `savings_goals`, `balance_snapshots`, `financial_events`, `loans`, `provisions`, `reimbursements`, `transactions`, `imports`, `recurring_transactions`, `salary`, `month_review`, `admin`, `exports`, `notifications`, `logos` | `investment_transactions`, `holdings`, `etf_profiles`, `market` → **phase 4** (liés à `core/holdings`, `portfolio`, `market_data`, `etf_analyzer`) |
| `core/` : `transfers`, `loans`, `provisions`, `reimbursements`, `splits`, `recurring`, `finance`, `salary`, `work_time`, `month_review`, `reconciliation`, `demo`, `seeds`, `notifications`, `currency`, `logos`, `backup` | `wealth`, `budget_period`, `subscription_prices`, `tax`, `tax_rules` → phase 3 ; `portfolio`, `holdings`, `dividends`, `market_data`, `etf_analyzer`, `seeds_etf` → phase 4 |

Ruling (plan maître) : les domaines d'écriture côté investissement passent en phase 4 avec le portefeuille ; les migrer ici imposerait de toucher deux fois `core/holdings` et les patchs de `market_data`.

## Global Constraints

- Aucun changement de comportement : mêmes routes, paramètres, codes et corps de réponse. Le serveur MCP ne doit rien voir.
- `main` vert après chaque tâche : `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q` (~750 tests, ~1 min 30) et `make check-size`.
- Commits directement sur `main`, un par tâche, terminés par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Plafonds : fichier Python 400 lignes, fonction 80 lignes. **En fin de tâche, toute entrée des deux baselines appartenant aux fichiers de la tâche a disparu** (la cible n'est plus « ne pas grossir » mais « sous le plafond »). Seule exception : un module `core/` déplacé à l'identique dans une tâche qui ne le découpe pas renomme sa clé de baseline sans changer la valeur.
- `tests/architecture_baseline.txt` reste **vide**.
- Code déplacé : supprimé de l'ancien emplacement, sans ré-export ; tous les importeurs mis à jour (absolus, relatifs, imports locaux, tests). Module `core/` déplacé : `git mv` puis édition, pour garder l'historique.
- **Patchs de test** : quand une fonction qui appelle un nom remplacé par un test (`monkeypatch.setattr(<module>, "<nom>", …)`) change de module, le test patche le nouveau module. Après la tâche 2, un patch devenu sans effet se voit : le réseau réel est bloqué.

### Correspondance des erreurs (routers → services)

| Aujourd'hui | Dans un service |
|---|---|
| `HTTPException(404)` / `api_error(404, code, …)` | `NotFoundError(detail[, code, context])` |
| 400 | `InvalidOperationError` (nouvelle, tâche 2) |
| 409 | `ConflictError` |
| 422 | `BusinessRuleError` |
| 500 | `InternalError` |
| 502 | `ExternalServiceError` (nouvelle, tâche 2) |
| 504 | `ExternalTimeoutError` (nouvelle, tâche 2) |
| 401, 403, 413, 429 | **restent dans `controllers/`** (authentification, taille d'upload, limiteur : préoccupations HTTP) |

Un `api_error(status, code, detail, context)` devient la classe correspondante avec `code=` et `context=` : corps identique.

### Recette d'un router (s'applique aux tâches 3 à 14 et 16)

1. **Repository** `app/repositories/<domaine>.py` : une fonction par requête (`get(db, id)`, `list_…(db, …)`, `add(db, obj)` = `db.add` + `flush`, `delete(db, obj)`, requêtes nommées par leur intention). Jamais de `commit`.
2. **Service** `app/services/<domaine>.py` : une fonction par route, **même nom que la fonction de route**, signature `(db: Session, <paramètres de la route hors db>)`, typée ; elle valide, appelle les repositories, `commit`, et renvoie le même objet que la route renvoyait. Helpers privés de router (`_check_…`, `_read`, `_get`) : dans le service.
3. **Router** : chaque route = sa signature + `return service.<nom>(db, …)` (ou `await`). Aucun import de `app.models`, aucun `db.query` / `commit`. Les en-têtes et codes HTTP (`status_code=201/204`, `Retry-After`, lecture d'`UploadFile`) restent dans le router.
4. **Tests de service** dans `backend/tests/test_<domaine>_service.py` (fixture `db_session`, sans HTTP) : au minimum les tests nommés dans la tâche, plus un test par erreur métier du domaine (`pytest.raises(<Classe>)`, message identique).
5. Vérifier : `grep -nE "db\.(query|add|commit|delete|get)|from app\.models" backend/app/controllers/<domaine>.py` → aucun résultat ; suite complète verte ; `make check-size` vert ; entrées de baseline du domaine retirées ; docs (`ARCHITECTURE.md` § Modules API, `backend/CLAUDE.md`, skills) mises à jour si un emplacement cité change.

## Review Focus

- **Patch devenu sans effet** : un test qui remplace `get_market_quotes`, `get_exchange_rates` ou `get_historical_rate` dans l'ancien module laisse le code déplacé appeler le vrai service. La tâche 2 bloque le réseau en test pour que ce cas échoue bruyamment, au lieu de passer ou d'échouer au hasard selon la connexion.
- **Import CSV idempotent** (règle métier 4) : le découpage de `commit_import` (201 lignes) ne doit changer ni la détection de doublons `(account_id, date, amount, merchant, type)`, ni le solde de départ, ni l'appel final à `recalculate_running_balances`. Test de caractérisation dans la tâche 10, avant découpage.
- **Frontière de transaction** : à la tâche 15, `recalculate_running_balances` cesse de commiter ; un appelant qui oubliait de commiter après perdrait les soldes. Chaque appelant est listé dans la tâche 15, avec un test qui relit les soldes dans une **nouvelle** session.
- **Salaire idempotent** (règle métier 6) : regénérer un mois déjà généré ne crée pas de deuxième « Salaire ». Test dans la tâche 13, avant découpage de `reset_generation` et `set_telecommuting_days`.
- **Suppressions en cascade manuelles** : `delete_category` remet à `NULL` six références avant de supprimer ; le déplacement vers le repository doit les garder toutes. Test dans la tâche 3.

---

### Task 1 : Renommer `api/` en `controllers/`

Demande de l'utilisateur (transmise par la session « Architecture refactoring avec clean archi ») : le dossier des routers porte le nom de sa couche. Fait en premier, pour que toutes les migrations suivantes écrivent directement dans `controllers/`.

**Files:**
- `git mv backend/app/api backend/app/controllers` (même structure interne : `controllers/accounts.py`, `controllers/analytics/…`, `controllers/deps.py` ; `backend/app/api/nodes.json` suit le déplacement, sa suppression reste un point à part). La variable `router = APIRouter(...)` ne change pas.
- Modify : `backend/app/main.py` ; tous les imports `app.api…` (absolus, relatifs, locaux dans les fonctions) dans `backend/app` ; tests (`conftest.py` : `get_db as get_db_deps`, `get_current_user` ; imports `app.api…` ; modules patchés `holdings_api`, `dividends_api` (`test_dividends.py`), `holdings_api` (`test_business_fixes.py`), `router_mod` (`test_month_review.py`), `diversity` (`test_etf_composition.py`), `portfolio` (`test_wealth_forecast.py`), `calc_diff` (`test_import_and_analytics.py`)).
- Modify : `backend/tests/test_architecture.py` et `architecture_baseline.txt` (toujours vide).
- Docs : `ARCHITECTURE.md` (§ Couches backend, arborescence, § Modules API), `CLAUDE.md` racine, `backend/CLAUDE.md`, `.claude/skills/numera-backend/SKILL.md`, `.claude/skills/numera-expert/SKILL.md`, `docs/ACTION_CENTER.md`, `docs/BACKEND.md`, la spec `docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md` et le plan maître (« `api/` » → « `controllers/` »).

**Interfaces:**
- Produces : package `app.controllers` (ex-`app.api`), `app.controllers.deps.get_db` / `get_current_user` / `optional_oauth2` / `require_interactive_session`, `app.controllers.analytics.router`.
- `test_architecture.py` : chaque `app.api` devient `app.controllers` dans `FORBIDDEN` (services, repositories, domain, integrations, core, models, schemas, db) ; la règle spéciale vise `app.controllers.X`, avec les mêmes exceptions (`app.controllers.deps`, sous-modules du même package).
- Aucun chemin HTTP ne change : préfixes `APIRouter(prefix=…)` intacts, frontend et serveur MCP inchangés.

- [ ] **Step 1 : Adapter les tests d'architecture** : renommer `test_api_may_import_deps_and_own_package_only` en `test_controllers_may_import_deps_and_own_package_only` (arbre temporaire sous `app/controllers/…`, violation attendue `app/controllers/month_review.py -> app.controllers.accounts`) ; ajouter `test_services_may_not_import_controllers` (`app/services/s.py` qui importe `app.controllers.deps` → violation). Les lancer → FAIL (règles encore écrites pour `app.api`).
- [ ] **Step 2 : Renommer** : `git mv`, puis remplacer `app.api` par `app.controllers` dans `backend/app` et `backend/tests` (imports `from app.api`, `import app.api… as …`, `from app import api` s'il existe) ; mettre `FORBIDDEN` et `_api_violation` (renommée `_controllers_violation`) à jour.
- [ ] **Step 3 : Vérifier** — `grep -rn "app\.api\b\|app/api/" backend mcp-server infra Makefile` → aucun résultat ; `APP_ENV=test PYTHONPATH=. python3.11 -c "import app.main"` ; suite complète verte ; `make check-size` (les clés de baseline `backend/app/api/…` deviennent `backend/app/controllers/…`, valeurs inchangées : régénérer puis vérifier que seules les clés ont changé) ; `architecture_baseline.txt` vide ; chemins HTTP identiques : comparer `sorted(r.path for r in app.routes)` avant et après le renommage.
- [ ] **Step 4 : Docs** : remplacer « `api/` » par « `controllers/` » dans les fichiers listés (hors historique des plans des phases déjà exécutées, qui reste tel quel) ; `grep -rn "app/api\|app\.api\|\bapi/" --include=*.md` ne renvoie plus que des chemins HTTP ou de l'historique.
- [ ] **Step 5 : Commit** — `refactor: le dossier des routers devient controllers/`

### Task 2 : Garde-fous de la phase 2

**Files:**
- Modify: `backend/tests/conftest.py`
- Modify: `backend/app/core/errors.py`
- Test: `backend/tests/test_domain_errors.py`, `backend/tests/test_network_guard.py` (nouveau)

**Interfaces:**
- Produces : `InvalidOperationError(DomainError)` 400, `ExternalServiceError(DomainError)` 502, `ExternalTimeoutError(DomainError)` 504 dans `app.core.errors`.
- Produces : fixture `autouse` `block_network` dans `conftest.py` qui remplace `httpx.HTTPTransport.handle_request` et `httpx.AsyncHTTPTransport.handle_async_request` par une fonction levant `RuntimeError("Réseau interdit en test : patcher l'appel externe")`. `httpx.MockTransport` reste utilisable (les tests ntfy / Telegram s'en servent).

- [ ] **Step 1 : Écrire les tests**
  - `test_domain_errors.py` : `test_invalid_operation_is_400`, `test_external_service_is_502`, `test_external_timeout_is_504` (corps `{"detail": …}`).
  - `test_network_guard.py` : `test_real_http_call_is_blocked` (`httpx.get("http://example.invalid")` lève `RuntimeError` dont le message contient « Réseau interdit ») ; `test_mock_transport_still_works` (`httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200)))` → 200).
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Implémenter** les trois classes et la fixture.
- [ ] **Step 4 : Suite complète.** Un test qui échoue avec « Réseau interdit » dépendait du réseau réel : patcher l'appel externe dans ce test (fonction factice comme les tests voisins), sans toucher au code applicatif. Ledger : une ligne par test corrigé.
- [ ] **Step 5 : Commit** — `test: réseau bloqué en test + erreurs métier 400/502/504`

### Task 3 : Catégories et tags

**Files:** Create `app/repositories/{categories,tags}.py`, `app/services/{categories,tags}.py`, `tests/test_categories_service.py`, `tests/test_tags_service.py` ; Modify `app/controllers/{categories,tags}.py`.

**Interfaces:**
- `services.categories` : `list_categories(db, include_archived: bool) -> list[Category]`, `create_category(db, payload: CategoryCreate) -> Category`, `update_category(db, category_id: int, payload: CategoryUpdate) -> Category`, `delete_category(db, category_id: int) -> None`.
- `repositories.categories.detach_references(db, category_id: int) -> None` : les sept `UPDATE … SET … = NULL` de l'actuel `delete_category` (transactions, objectifs d'épargne, règles, récurrences, marchands, `salary_category_id`, `ticket_category_id`).
- `services.tags` : `list_tags`, `create_tag`, `update_tag`, `delete_tag`, mêmes signatures sur le modèle de `categories`.

- [ ] **Step 1 : Tests**
  - `test_delete_category_detaches_every_reference` : une catégorie référencée par une transaction, une règle, un marchand et la config salaire (salaire + TR) ; après `delete_category`, ces cinq références valent `None` et la catégorie n'existe plus.
  - `test_create_duplicate_category_is_conflict` : `ConflictError`, `to_content()["detail"]["code"] == "category_already_exists"`.
  - `test_duplicate_tag_name_is_invalid_operation` : `InvalidOperationError("Tag name already exists")`.
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Appliquer la recette** aux deux routers.
- [ ] **Step 4 : Vérifier** (recette, étape 5).
- [ ] **Step 5 : Commit** — `refactor(categories, tags): router/service/repository`

### Task 4 : Marchands et règles de catégorisation

**Files:** Create `app/repositories/{merchants,categorization_rules}.py`, `app/services/{merchants,categorization_rules}.py`, `tests/test_merchants_service.py` ; Modify `app/controllers/{merchants,categorization_rules}.py`.

**Interfaces:**
- `services.merchants` : `get_merchants(db, skip, limit, search)`, `create_merchant(db, merchant_in)`, `get_merchant(db, merchant_id)`, `update_merchant(db, merchant_id, merchant_in)`, `delete_merchant(db, merchant_id)`, `add_alias(db, merchant_id, alias_in)`, `remove_alias(db, alias_id)`, `auto_normalize_transactions(db)`, `get_unnormalized_merchant_labels(db, min_count)` ; `_link_matching_transactions` devient `link_matching_transactions(db, merchant) -> int` (public : `auto_normalize` et `create_merchant` l'utilisent).
- `services.categorization_rules` : `list_rules`, `create_rule`, `update_rule`, `delete_rule`, `apply_rules_to_transactions(db) -> dict` (53 lignes : garder sous 80, la boucle de recalcul des soldes appelle `recalculate_running_balances` par compte touché).

- [ ] **Step 1 : Tests** : `test_create_merchant_links_existing_transactions` (deux transactions au libellé de l'alias reçoivent le `merchant_id`, le libellé bancaire `merchant` est inchangé — règle métier 7) ; `test_duplicate_alias_is_conflict` (`ConflictError("Cet alias existe déjà")`) ; `test_apply_rules_categorizes_and_keeps_balances` (une règle sur « CARREFOUR » catégorise la transaction ; `running_balance` inchangé).
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Recette.**
- [ ] **Step 4 : Vérifier.**
- [ ] **Step 5 : Commit** — `refactor(merchants, categorization_rules): router/service/repository`

### Task 5 : Virements internes (règles et moteur)

**Files:** `git mv app/core/transfers.py app/services/transfers.py` ; Create `app/repositories/transfers.py`, `app/services/transfer_rules.py`, `app/repositories/transfer_rules.py`, `tests/test_transfer_rules_service.py` ; Modify `app/controllers/transfer_rules.py` et tous les importeurs de `app.core.transfers` (`controllers/transactions.py`, `controllers/imports.py`, `core/recurring.py`, tests `test_transfers.py`, `test_transfer_engine.py`, …).

**Interfaces:**
- `services.transfers` garde ses noms publics (`auto_link_transfers`, `candidates_for`, `create_counterpart`, `find_pairs`, `link_pair`, `release_partner`, `unlink_pair`, `apply_rules`). Ses requêtes passent dans `repositories.transfers`.
- `find_pairs` (115 lignes) est découpé sous 80 lignes : `_candidate_debits(db, …)`, `_candidate_credits(db, …)` dans le repository, appariement pur dans `domain/transfers.py::match_pairs(debits, credits, days_tolerance: int, amount_tolerance_pct: float) -> list[tuple[int, int]]`.
- `services.transfer_rules` : `list_rules`, `create_rule`, `update_rule`, `delete_rule`, `apply_transfer_rules(db, dry_run: bool, rule_id: int | None)` ; `_check_accounts` lève `BusinessRuleError("Source and destination accounts must differ")`.

- [ ] **Step 1 : Tests** : `test_match_pairs_respects_amount_tolerance` (domaine pur : un débit de 100 et un crédit de 101 s'apparient à 2 %, pas à 0,5 %) ; `test_match_pairs_respects_day_tolerance` ; `test_rule_with_same_source_and_destination_is_rejected` (`BusinessRuleError`).
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Déplacer, découper, appliquer la recette.**
- [ ] **Step 4 : Vérifier** — entrées `core/transfers.py` et `::find_pairs` absentes de la baseline de taille.
- [ ] **Step 5 : Commit** — `refactor(transfers): moteur et règles de virements dans services/, appariement pur dans domain/`

### Task 6 : Objectifs d'épargne, relevés de solde, événements financiers

**Files:** Create `app/repositories/{savings_goals,balance_snapshots,financial_events}.py`, `app/services/{savings_goals,balance_snapshots,financial_events}.py`, `tests/test_balance_snapshots_service.py` ; Modify les trois routers.

**Interfaces:**
- `services.savings_goals` : `list_goals(db) -> list[SavingsGoalRead]` découpé sous 80 lignes (calcul de progression par objectif dans `_goal_progress(db, goal, rates) -> SavingsGoalRead`), `create_goal`, `update_goal`, `delete_goal`.
- `services.balance_snapshots` : `list_balance_snapshots(db, account_id)`, `create_balance_snapshot(db, payload)`, `delete_balance_snapshot(db, snapshot_id)`, `update_balance_snapshot(db, snapshot_id, payload)`, `set_zero_point(db, payload)` ; la vérification « compte investissement ou assurance-vie » est un helper unique `_require_valued_account(db, account_id) -> Account`.
- `services.financial_events` : `list_financial_events(db, start, end, account_id)`, `create_…`, `update_…`, `delete_…`.

- [ ] **Step 1 : Tests** : `test_snapshot_on_current_account_is_rejected` (`BusinessRuleError("Account must be of type investissement or assurance_vie")`) ; `test_set_zero_point_keeps_a_single_zero_point` (règle métier 5 : deux appels successifs → un seul `is_zero_point=True` sur le compte).
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Recette.**
- [ ] **Step 4 : Vérifier** — `savings_goals.py::list_goals` absente de la baseline.
- [ ] **Step 5 : Commit** — `refactor(savings_goals, balance_snapshots, financial_events): router/service/repository`

### Task 7 : Crédits et provisions

**Files:** `git mv app/core/loans.py app/domain/loans.py` ; `git mv app/core/provisions.py app/services/provisions.py` ; Create `app/services/loans.py`, `app/repositories/{loans,provisions}.py`, `tests/test_loans_service.py` ; Modify `app/controllers/{loans,provisions}.py`, `app/services/accounts.py`, `tests/test_loans_core.py`, `tests/test_provisions.py`.

**Interfaces:**
- `domain.loans` : uniquement les fonctions pures actuelles (`add_months`, `terms_of`, échéancier, simulation). `loan_remaining(db, account_id, at)` (requête) part dans `services.loans`.
- `services.loans` : `loan_remaining(db, account_id: int, at: date) -> float | None` + une fonction par route (`list_loans`, `create_loan`, `get_loan_by_account`, `get_loan`, `update_loan`, `delete_loan`, `get_schedule`, `simulate`, `add_prepayment`, `delete_prepayment`). `create_loan` / `delete_loan` créent et suppriment le compte `credit` avec le prêt, dans un seul commit.
- `services.accounts.account_balance` importe `loan_remaining` depuis `services.loans`.
- `services.provisions` : fonctions actuelles de `core/provisions.py` + routes (`list_provisions`, `provisions_summary`, `create_provision`, `update_provision`, `delete_provision`).

- [ ] **Step 1 : Tests** : `test_create_loan_creates_credit_account` (un compte `type="credit"` existe, `account_balance` vaut −capital restant dû) ; `test_delete_loan_removes_credit_account`.
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Déplacer et appliquer la recette.**
- [ ] **Step 4 : Vérifier** — `domain/loans.py` passe le test d'architecture (aucune `Session`).
- [ ] **Step 5 : Commit** — `refactor(loans, provisions): calculs de crédit dans domain/, cas d'usage dans services/`

### Task 8 : Remboursements et découpages

**Files:** `git mv app/core/reimbursements.py app/services/reimbursements.py` ; `git mv app/core/splits.py app/services/splits.py` ; Create `app/repositories/reimbursements.py`, `tests/test_splits_service.py` ; Modify `app/controllers/reimbursements.py` et tous les importeurs de `app.core.reimbursements` (`remb`) et `app.core.splits`.

**Interfaces:**
- `services.reimbursements` et `services.splits` n'importent plus `fastapi` : 400 → `InvalidOperationError`, 404 → `NotFoundError`, messages identiques (`"Seule une dépense (hors virement interne) peut être découpée"`, `"Un découpage compte au moins deux parts"`, `"Annulez le découpage avant de changer le type de cette dépense"`, …).
- Le helper qui levait `HTTPException(400, detail)` dans `core/reimbursements.py:28` lève `InvalidOperationError(detail)`.
- Routes de `controllers/reimbursements.py` : une fonction de service par route (`list_claims`, `reimbursement_summary`, `create_claim`, `update_claim`, `delete_claim`, `claim_candidates`, `allocate`, `remove_allocation`, `entry_claims`).

- [ ] **Step 1 : Tests** : `test_split_of_income_is_invalid_operation` ; `test_split_with_one_part_is_invalid_operation` ; `test_changing_amount_of_split_expense_is_invalid_operation` (messages exacts ci-dessus).
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Déplacer, convertir les erreurs, appliquer la recette.**
- [ ] **Step 4 : Vérifier** — `grep -rn "fastapi" backend/app/services backend/app/core/splits.py` → aucun résultat ; suite verte (`test_transaction_splits.py`, `test_reimbursements.py`, `test_reimbursement_kpis.py`).
- [ ] **Step 5 : Commit** — `refactor(reimbursements, splits): services sans HTTPException`

### Task 9 : Transactions, lecture

**Files:** Create `app/repositories/transactions.py`, `app/services/transactions.py`, `tests/test_transactions_service.py` ; Modify `app/controllers/transactions.py`.

**Interfaces:**
- `repositories.transactions.filtered_query(db, filters: TransactionFilters)` : construit la requête de `list_transactions` ; `TransactionFilters` = dataclass (dans le repository) avec exactement les 17 filtres de la route (`account_id`, `category_id`, `type`, `merchant`, `month`, `year`, `min_amount`, `max_amount`, `start_date`, `end_date`, `is_transfer`, `tag_ids`, `search`, `uncategorized`, `merchant_name`, `period`, `budget_scope`).
- `services.transactions` (lecture) : `list_transactions(db, filters: TransactionFilters, skip: int, limit: int) -> list[Transaction]` (sous 80 lignes), `list_merchants(db)`, `find_potential_transfers(db, days_tolerance, amount_tolerance_pct, months)`, `transfer_candidates(db, transaction_id, days, amount_tolerance_pct, account_id)`.
- La route `list_transactions` garde ses 19 paramètres `Query` et construit `TransactionFilters` (le router reste le seul à connaître `Query`).

- [ ] **Step 1 : Tests** : `test_budget_scope_excludes_ticket_restaurant_accounts` (un compte nommé « Tickets Restaurant » est exclu avec `budget_scope=True`) ; `test_category_filter_includes_split_parts` (une dépense découpée apparaît pour la catégorie d'une de ses parts — `category_lines`) ; `test_service_matches_http_route` (paramétré sur trois jeux de filtres : `budget_scope`, `category_id` + découpage, `period` ; le service renvoie les mêmes ids, dans le même ordre, que `GET /transactions` avec les mêmes paramètres).
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Recette pour les quatre routes de lecture.**
- [ ] **Step 4 : Vérifier** — `transactions.py::list_transactions` absente de la baseline ; suite verte (`test_filtering.py`, `test_transfers.py`).
- [ ] **Step 5 : Commit** — `refactor(transactions): lecture et filtres dans services/repositories`

### Task 10 : Import CSV

**Files:** Create `app/domain/csv_import.py`, `app/services/imports.py`, `app/repositories/imports.py`, `tests/test_csv_import_domain.py` ; Modify `app/controllers/imports.py`, `tests/test_import_formats.py` (importe `_parse_amount`).

**Interfaces:**
- `domain.csv_import` (pur, sans `UploadFile`) : `HEADER_ALIASES`, `normalize_header(h: str) -> str`, `read_csv(text: str) -> tuple[list[str], list[dict]]` (détection `,` `;` `\t`), `canonicalize_row(row: dict) -> dict`, `parse_date(value: str) -> datetime`, `parse_amount(value: str) -> float`, `parse_row(row: dict, …) -> ParsedRow` (dataclass), `duplicate_key(account_id, date, amount, merchant, type) -> tuple`.
- `services.imports` : `get_import_logs(db, limit)`, `preview_import(db, content: bytes, filename: str, sample_size: int)`, `commit_import(db, account_id: int, content: bytes, filename: str, create_missing_categories: bool, category_mapping: dict | None)`. `commit_import` (201 lignes) découpé en étapes de moins de 80 lignes : `_map_categories`, `_existing_keys`, `_insert_rows`, `_log_import`.
- Le router garde `_read_upload` (lecture de l'`UploadFile`, 413 si trop gros) et passe `bytes` au service.

- [ ] **Step 1 : Test de caractérisation, avant tout déplacement** (`test_import_and_analytics.py` couvre l'essentiel ; ajouter s'il manque) `test_reimporting_same_file_inserts_nothing` : importer deux fois le même CSV de 3 lignes via `client` → deuxième import `imported == 0`, 3 transactions en base, `running_balance` de la dernière égal au solde attendu. Le lancer : PASS.
- [ ] **Step 2 : Tests de domaine** : `test_parse_amount_accepts_french_format` (`"1 234,56"` → `1234.56`), `test_parse_amount_accepts_negative_with_minus` (même valeur absolue que le comportement actuel : le lire dans `_parse_amount`), `test_read_csv_detects_semicolon`, `test_normalize_header_maps_aliases` (un alias réel de `HEADER_ALIASES`). Les lancer → FAIL.
- [ ] **Step 3 : Déplacer, découper, appliquer la recette.**
- [ ] **Step 4 : Vérifier** — `controllers/imports.py` et `::commit_import` absentes de la baseline ; suite verte dont le test du step 1.
- [ ] **Step 5 : Commit** — `refactor(imports): analyse CSV pure dans domain/, import en étapes dans services/`

### Task 11 : Transactions, écriture

**Files:** Modify `app/services/transactions.py`, `app/repositories/transactions.py`, `app/controllers/transactions.py`, `tests/test_transactions_service.py`.

**Interfaces:**
- `services.transactions` (écriture) : `create_transaction(db, payload)`, `update_transaction(db, transaction_id, payload)` (85 lignes → sous 80 : `_apply_amount_change`, `_apply_transfer_change`), `delete_transaction`, `bulk_update_transactions`, `bulk_delete_transactions`, `update_transaction_splits`, `create_transfer_counterpart`, `link_transactions`, `ignore_transfer`, `ignore_duplicate`, `unlink_transaction` (toutes async si elles convertissent une devise).
- `validate_solde_initial(db, account_id, date, exclude_id=None)` passe dans `services.transactions` et lève `BusinessRuleError` (422, messages identiques).

- [ ] **Step 1 : Tests** : `test_second_initial_balance_is_rejected` (`BusinessRuleError("A Solde Initial already exists for this account")`) ; `test_update_amount_recalculates_following_balances` ; `test_bulk_delete_recalculates_each_account_once` (deux comptes touchés → les soldes des deux sont justes).
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Recette pour les 11 routes d'écriture.**
- [ ] **Step 4 : Vérifier** — `controllers/transactions.py` et `::update_transaction` absentes de la baseline ; `controllers/transactions.py` < 400 lignes ; suite verte (`test_transaction_*.py`, `test_business_fixes.py`).
- [ ] **Step 5 : Commit** — `refactor(transactions): écriture dans services/`

### Task 12 : Récurrences et règles financières pures

**Files:** `git mv app/core/finance.py app/domain/finance.py` ; `git mv app/core/recurring.py app/services/recurring.py` ; Create `app/services/recurring_transactions.py`, `app/repositories/recurring.py`, `tests/test_recurring_service.py` ; Modify `app/controllers/recurring_transactions.py`, `app/main.py` (tâche de fond), tous les importeurs de `app.core.finance` (17) et `app.core.recurring`.

**Interfaces:**
- `domain.finance` : fonctions pures actuelles (`apply_transaction_to_balance`, `month_label_from_date`, `normalize_transaction_type`, `is_lapsed`, `get_recurring_occurrences` découpée sous 80 lignes).
- `services.recurring.generate_recurring_transactions(db) -> int` (188 lignes) découpée par type de récurrence (`_generate_cash_occurrence`, `_generate_security_purchase`, `_generate_transfer`), chacune < 80 lignes ; `transfer_credit_date` reste public.
- `services.recurring_transactions` : `read_recurring_transactions`, `create_recurring_transaction`, `update_recurring_transaction`, `delete_recurring_transaction`, `trigger_generation` ; `_validate_transfer_target` lève `BusinessRuleError` (messages identiques).

- [ ] **Step 1 : Tests** : `test_generation_is_idempotent` (deux passages le même jour → mêmes transactions, aucune en double ; caractérisation, PASS attendu) ; `test_occurrences_skip_lapsed_recurrence` (domaine : une récurrence dont la date de fin est passée ne produit aucune occurrence future, avec la signature actuelle de `get_recurring_occurrences`).
- [ ] **Step 2 : Les lancer** — le premier passe, le second échoue sur l'import `app.domain.finance`.
- [ ] **Step 3 : Déplacer, découper, appliquer la recette** ; la tâche de fond de `main.py` importe `services.recurring`.
- [ ] **Step 4 : Vérifier** — `core/recurring.py::generate_recurring_transactions` et `core/finance.py::get_recurring_occurrences` absentes de la baseline ; suite verte (`test_recurring_*.py`, `test_lapsed_recurring.py`).
- [ ] **Step 5 : Commit** — `refactor(recurring): génération dans services/, règles financières pures dans domain/`

### Task 13 : Salaire et temps de travail

**Files:** `git mv app/core/salary.py app/services/salary_generation.py` ; `git mv app/core/work_time.py app/domain/work_time.py` (une éventuelle requête part dans `services/salary.py`) ; Create `app/services/salary.py`, `app/repositories/salary.py`, `app/domain/salary.py`, `tests/test_salary_service.py` ; Modify `app/controllers/salary.py`, `app/main.py`, `tests/test_salary_*.py`, `tests/test_work_time.py`.

**Interfaces:**
- `domain.salary.salary_amount(net_salary: float, telework_days: int, ticket_employee_share: float) -> float` = `net_salary − telework_days × ticket_employee_share` (règle métier 6), utilisée par `services.salary_generation`.
- `services.salary` : une fonction par route du router salaire (`get_salary_config`, `create_salary_config`, `update_salary_config`, `get_work_time`, `update_work_time`, `get_salary_months`, `set_salary_month_date`, `get_telecommuting_days`, `set_telecommuting_days`, `get_month_summary`, `trigger_generation`, `reset_generation`) et `sync_recurring_transactions` ; `reset_generation` (83 lignes) et `set_telecommuting_days` (75) < 80 lignes. 400 → `InvalidOperationError`, 422 → `BusinessRuleError`.
- `controllers/salary.py` < 400 lignes.

- [ ] **Step 1 : Tests** : `test_regenerating_salary_month_keeps_single_salary` (générer deux fois le même mois → une seule `Entree` « Salaire » ; caractérisation, PASS attendu) ; `test_salary_amount_subtracts_telework_tickets` (`salary_amount(2500, 10, 4.5) == 2455.0`, FAIL attendu : fonction absente).
- [ ] **Step 2 : Les lancer.**
- [ ] **Step 3 : Déplacer, découper, appliquer la recette** ; la tâche de fond importe `services.salary_generation`.
- [ ] **Step 4 : Vérifier** — `controllers/salary.py` et `::reset_generation` absentes de la baseline ; suite verte (`test_salary_*.py`, `test_telecommuting_validation.py`, `test_work_time.py`).
- [ ] **Step 5 : Commit** — `refactor(salary): router/service/repository, montant du salaire dans domain/`

### Task 14 : Revue de mois et rapprochement bancaire

**Files:** `git mv app/core/month_review.py app/services/month_review.py` ; `git mv app/core/reconciliation.py app/services/reconciliation.py` ; Create `app/repositories/month_review.py` ; Modify `app/controllers/month_review.py`, `app/services/accounts.py`, `app/services/analytics/*` et `app/controllers/analytics/*` qui importent `core.month_review`, `tests/test_month_review.py` (le patch `router_mod` vise le nouveau module qui appelle `get_exchange_rates`).

**Interfaces:**
- `services.month_review` : contenu actuel de `core/month_review.py` + `_accounts_step`, `_build_review`, `get_month_review`, `close_month`, `reopen_month`, `list_closures` (règle métier 10 : clôturer = marquer, jamais verrouiller).
- `services.reconciliation.reconcile` (94 lignes) < 80 lignes (`_hints(…)` extrait).

- [ ] **Step 1 : Test** : `test_closed_month_stays_editable` (clôturer, puis modifier une transaction du mois via le service des transactions : réussit, `modified_since_close` devient vrai) ; caractérisation, PASS attendu.
- [ ] **Step 2 : Le lancer.**
- [ ] **Step 3 : Déplacer, découper, appliquer la recette.**
- [ ] **Step 4 : Vérifier** — `core/reconciliation.py::reconcile` absente de la baseline ; suite verte (`test_month_review.py`, `test_mcp_month_review_tools.py`, `test_reconciliation.py`, `test_exceptional_flag.py`).
- [ ] **Step 5 : Commit** — `refactor(month_review, reconciliation): services/`

### Task 15 : Frontière de transaction des soldes

**Files:** Modify `app/services/balances.py` et chacun de ses appelants (à date : `services/transactions.py`, `services/imports.py`, `services/categorization_rules.py`, `services/salary.py`, `services/salary_generation.py`, `services/recurring.py`, `core/demo.py`, tests `test_reconciliation.py`, `test_wrapped.py`) — liste à confirmer par `grep -rn "recalculate_running_balances" backend`.
- Test: `backend/tests/test_balances_service.py`

**Interfaces:**
- `services.balances.recalculate_running_balances(db, account_id) -> None` : `db.flush()` au lieu de `db.commit()`. Chaque appelant commit **après** son dernier recalcul (la plupart le font déjà ; sinon ajouter le `db.commit()`).

- [ ] **Step 1 : Tests** : `test_recalculate_does_not_commit` (recalcul puis `db_session.rollback()` → `running_balance` revenu à l'ancienne valeur) → FAIL aujourd'hui ; pour chaque route qui recalcule (création, modification, suppression, bulk, import, application des règles, génération de salaire), `test_<route>_persists_balances` relit les soldes dans une **session neuve** (`sessionmaker` lié au même engine) après l'appel `client`.
- [ ] **Step 2 : Les lancer** → le premier FAIL, les autres PASS (caractérisation).
- [ ] **Step 3 : Passer en `flush`, ajouter les `commit` manquants.**
- [ ] **Step 4 : Vérifier** — suite complète verte, dont tous les tests du step 1.
- [ ] **Step 5 : Commit** — `refactor(balances): le recalcul ne commit plus, l'appelant porte la transaction`

### Task 16 : Administration, export, démo, données initiales

**Files:** `git mv app/core/demo.py app/services/demo/__init__.py` puis découpe ; `git mv app/core/seeds.py app/services/seeds.py` ; Create `app/services/{admin,exports}.py`, `app/repositories/admin.py` ; Modify `app/controllers/{admin,exports}.py`, `app/main.py` (`ensure_demo_data`, `is_blocked_in_demo`, `seed_all`), `tests/test_demo.py`, `tests/test_sensitive_actions.py`.

**Interfaces:**
- `services/demo/` : `guard.py` (`is_blocked_in_demo(method, path) -> bool`, `DEMO_STAMP_KEY`), `generator.py` (`generate_demo_data(db)` et ses helpers, chaque fichier < 400 lignes, chaque fonction < 80), `__init__.py` (`ensure_demo_data`, `wipe_database`, ré-exports **internes au package** autorisés car c'est l'API publique du package).
- `services.admin` : `get_admin_profile`, `update_admin_profile`, `list_login_events`, `logout_all_sessions`, `list_mcp_tokens`, `create_mcp_token`, `revoke_mcp_token`, `reset_database`, `run_backup_now` (504 → `ExternalTimeoutError("La sauvegarde a dépassé le délai imparti")`), `get_backup_status`. `_require_current_password` lève `InvalidOperationError` (400, jamais 401/403 : le client déconnecte sur ces codes).
- `services.exports.export_transactions_csv(db, account_ids) -> str` (99 lignes → < 80 : `_row(tx, …) -> list[str]`) ; le router construit la `StreamingResponse`.

- [ ] **Step 1 : Tests** : `test_wrong_current_password_is_400_not_401` (service : `InvalidOperationError`) ; `test_export_neutralizes_formula_injection` (un marchand `=HYPERLINK(...)` sort préfixé, comme `_csv_safe` aujourd'hui) ; `test_demo_guard_blocks_admin_writes` (si absent de `test_demo.py`).
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Déplacer, découper, appliquer la recette.**
- [ ] **Step 4 : Vérifier** — `core/demo.py`, `controllers/exports.py::export_transactions_csv` absentes de la baseline ; suite verte (`test_demo.py`, `test_sensitive_actions.py`, `test_security_*.py`).
- [ ] **Step 5 : Commit** — `refactor(admin, exports, demo): services/ et démo découpée`

### Task 17 : Intégrations externes et notifications

**Files:** `git mv app/core/currency.py app/integrations/currency.py` ; `git mv app/core/logos.py app/integrations/logos.py` ; `git mv app/core/backup.py app/integrations/backup.py` ; `git mv app/core/notifications.py app/services/notifications.py` puis extraire `app/integrations/notifications.py` ; Create `app/services/logos.py` si le router `logos` contient de la logique ; Modify `app/controllers/{notifications,logos}.py`, tous les importeurs de `app.core.currency` (24) / `logos` / `backup` / `notifications`, `app/main.py`, et les tests qui patchent `currency_mod`, `currency_module`, `logos`, `notif`.

**Interfaces:**
- `integrations.currency` : noms publics inchangés (`get_exchange_rates`, `convert_amount`, `get_historical_rate`, `CurrencyConversionError`, `_rates_cache`, `_cache_expiry`).
- `integrations.notifications` : classes de canaux (`NtfyChannel`, `TelegramChannel`), `send_all(channels, title, body, priority, url)`.
- `services.notifications` : réglages, détection des nouvelles actions, résumé hebdo, `run_notifications(db)`, `enabled_channels(db)` ; `send_test_notification` lève `InvalidOperationError` (400) si incomplet, `ExternalServiceError` (502) si l'envoi échoue, messages identiques.
- `main.py` : handler `CurrencyConversionError` importé depuis `integrations.currency`.

- [ ] **Step 1 : Lister les patchs à migrer** : `grep -rn "currency_mod\|currency_module\|import app.core.notifications\|core import logos\|core.backup" backend/tests` ; chaque fichier listé est modifié dans cette tâche.
- [ ] **Step 2 : Test** : `test_send_test_notification_failure_is_502` (service, canal factice qui lève `httpx.TimeoutException` → `ExternalServiceError`) → FAIL.
- [ ] **Step 3 : Déplacer, extraire les canaux, mettre à jour importeurs et patchs.**
- [ ] **Step 4 : Vérifier** — `grep -rn "app.core.\(currency\|logos\|backup\|notifications\)" backend` → aucun résultat ; suite verte sans « Réseau interdit » ; `integrations/` ne dépend ni de `services` ni de `repositories` (test d'architecture).
- [ ] **Step 5 : Commit** — `refactor: Frankfurter, logos, sauvegardes et canaux de notification dans integrations/`

### Task 18 : Clôture de la phase 2

**Files:** `ARCHITECTURE.md`, `CLAUDE.md`, `backend/CLAUDE.md`, `.claude/skills/numera-backend/SKILL.md`, `.claude/skills/numera-expert/SKILL.md`, `docs/BACKEND.md`, `docs/superpowers/plans/2026-10-28-architecture-en-couches.md`.

- [ ] **Step 1 : Vérifier le périmètre** : aucun router de la phase 2 n'importe `app.models` ni ne fait `db.query` (`grep` sur les 20 fichiers) ; `ls backend/app/core` ne contient plus que le transverse et les modules reportés (phase 3 : `wealth`, `budget_period`, `subscription_prices`, `tax`, `tax_rules` ; phase 4 : `portfolio`, `holdings`, `dividends`, `market_data`, `etf_analyzer`, `seeds_etf`).
- [ ] **Step 2 : Docs** : arborescence et § Couches de `ARCHITECTURE.md`, emplacements cités dans les `CLAUDE.md` et skills (`grep -rn "core/\(transfers\|loans\|provisions\|reimbursements\|splits\|recurring\|finance\|salary\|work_time\|month_review\|reconciliation\|demo\|seeds\.py\|notifications\|currency\|logos\|backup\)" --include=*.md` hors `docs/superpowers/` → aucun résultat). Plan maître : phase 2 marquée terminée, domaines d'investissement ajoutés à la phase 4.
- [ ] **Step 3 : Suite complète, `make check-size`, `cd frontend && npm run build`.**
- [ ] **Step 4 : Commit** — `docs: phase 2 de la migration en couches terminée`
