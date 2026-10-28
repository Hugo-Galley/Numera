# Migration vers une architecture en couches — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Séparer le backend en couches `api → services → repositories / domain / integrations`, découper les fichiers et fonctions géants (backend puis frontend), sans changer aucun comportement observable.

**Architecture:** Migration progressive. Phase 0 pose deux garde-fous automatiques à cliquet (taille, règles d'import). Phase 1 casse les dépendances inversées et migre `accounts`, qui sert de modèle. Les phases 2 à 6 suivent la même recette, domaine par domaine ; chacune reçoit son plan détaillé à son ouverture (le détail dépend du code tel qu'il sera après la phase 1).

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic v2, pytest (Python 3.11/3.12) ; React 18 + TypeScript (frontend, phase 5).

**Spec:** `docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md`

## Global Constraints

- Aucun changement de comportement : mêmes routes, mêmes paramètres, mêmes corps de réponse (y compris les erreurs), même base. Le serveur MCP ne doit rien voir.
- `main` reste vert après chaque tâche : `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q` passe (366 tests + ceux ajoutés) et `cd frontend && npm run build` passe.
- Commits directement sur `main`, un par tâche, terminés par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Plafonds : fichier Python 400 lignes, fonction Python 80 lignes, fichier `.ts`/`.tsx` 350 lignes (hors `frontend/src/components/ui/`).
- Les baselines (`scripts/code_size_baseline.json`, `backend/tests/architecture_baseline.txt`) ne peuvent que diminuer. Seule exception : un déplacement de code **à l'identique** renomme la clé de baseline en gardant la même valeur. Jamais d'augmentation.
- Un repository ne fait jamais `commit()` ; un service ne lève jamais `HTTPException` et n'importe pas `fastapi`.
- Chaque helper déplacé : mettre à jour **tous** les importeurs (absolus `from app.api…` **et** relatifs `from .utils`, y compris les imports locaux dans les fonctions et les tests), sans laisser de ré-export dans l'ancien module.
- Quand une route, une commande ou une règle change de place : mettre à jour `ARCHITECTURE.md` et, si besoin, `backend/CLAUDE.md` et `.claude/skills/numera-backend/SKILL.md` dans le même commit.

## Review Focus

- Format des erreurs : une `HTTPException(404, "Account not found")` devenue `NotFoundError` doit renvoyer exactement `{"detail": "Account not found"}` (le frontend lit `detail` via `errorMessage`). Test dans la tâche 3.
- Frontière de transaction : un service qui écrit puis échoue ne doit pas laisser d'écriture partielle commitée par un repository. Règle « pas de `.commit(` dans `repositories/` » vérifiée par la tâche 2.
- Digest des notifications : `_digest_body` avale les exceptions (`logger.warning`), donc une signature cassée ferait disparaître des lignes sans faire échouer de test. Test dans la tâche 6.
- Imports circulaires à l'exécution : plusieurs imports étaient locaux justement pour éviter un cycle. Le `conftest.py` importe `app.main`, donc toute la suite le couvre ; ne pas transformer un import local en import de module sans relancer la suite.
- Code `async` : les fonctions déplacées qui font `await get_exchange_rates(...)` restent `async`, et leurs appelants les `await`.

---

## Phase 0 — Garde-fous

### Task 1 : Garde-fou de taille (fichiers et fonctions)

**Files:**
- Create: `scripts/check_code_size.py`
- Create: `scripts/code_size_baseline.json` (générée)
- Create: `backend/tests/test_code_size_guard.py`
- Modify: `Makefile` (cible `check-size`, ajoutée à `validate`)

**Interfaces:**
- Produces, dans `scripts/check_code_size.py` (bibliothèque standard uniquement) :
  - `LIMITS = {"py_file": 400, "py_function": 80, "ts_file": 350}`
  - `measure(repo_root: Path) -> dict[str, int]` : clés relatives à la racine du dépôt. `backend/app/x.py` → lignes du fichier ; `backend/app/x.py::Classe.methode` ou `::externe.interne` → lignes de la fonction (`end_lineno - lineno + 1`, décorateurs exclus, via `ast`) ; `frontend/src/x.tsx` → lignes. Seules les mesures **au-dessus du plafond** sont renvoyées. Ignore `__pycache__`, `frontend/src/components/ui/` et `*.d.ts`.
  - `check(measures: dict[str, int], baseline: dict[str, int]) -> list[str]` : un message par erreur (nouvelle entrée hors baseline ; entrée de baseline qui a grossi ; entrée de baseline absente des mesures, donc à retirer).
  - `main(argv: list[str] | None = None) -> int` : `--write-baseline` écrit les mesures courantes (JSON trié, indenté) et renvoie 0 ; sinon affiche les erreurs et renvoie 1 s'il y en a.

- [ ] **Step 1 : Écrire les tests** dans `backend/tests/test_code_size_guard.py`, avec le module chargé par `importlib.util.spec_from_file_location` depuis `Path(__file__).parents[2] / "scripts/check_code_size.py"`.

```python
def test_new_oversized_file_fails(tmp_path):
    write(tmp_path / "backend/app/big.py", "x = 1\n" * 401)
    assert len(guard.check(guard.measure(tmp_path), {})) == 1

def test_baselined_file_may_not_grow():
    assert guard.check({"backend/app/big.py": 450}, {"backend/app/big.py": 420})

def test_baselined_file_back_under_limit_must_be_removed():
    assert guard.check({}, {"backend/app/big.py": 420})

def test_long_function_has_qualified_key(tmp_path):
    body = "class A:\n    def m(self):\n" + "        x = 1\n" * 85
    write(tmp_path / "backend/app/a.py", body)
    assert "backend/app/a.py::A.m" in guard.measure(tmp_path)

def test_ui_components_are_ignored(tmp_path):
    write(tmp_path / "frontend/src/components/ui/table.tsx", "x\n" * 500)
    assert guard.measure(tmp_path) == {}

def test_repository_matches_baseline():
    root = Path(__file__).parents[2]
    baseline = json.loads((root / "scripts/code_size_baseline.json").read_text())
    assert guard.check(guard.measure(root), baseline) == []
```

(`write` = petit helper local qui crée les dossiers parents puis écrit le fichier.)

- [ ] **Step 2 : Lancer les tests et constater l'échec**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_code_size_guard.py -v`
Expected: FAIL (le script n'existe pas).

- [ ] **Step 3 : Implémenter `scripts/check_code_size.py`** selon les interfaces ci-dessus, puis générer la baseline : `python3.11 scripts/check_code_size.py --write-baseline`. Elle doit au minimum contenir `backend/app/api/analytics/investments.py`, `backend/app/api/analytics/budget.py::budget_analytics`, `backend/app/api/analytics/audit.py::get_action_center`, `backend/app/core/portfolio.py::compute_portfolio` et `frontend/src/pages/AccountDetail.tsx`.

- [ ] **Step 4 : Ajouter au `Makefile`** une cible `check-size: ; python3 scripts/check_code_size.py`, et la mettre dans `validate: check-size test frontend-build`.

- [ ] **Step 5 : Vérifier**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q && cd .. && make check-size`
Expected: tous les tests PASS ; `check-size` sort en 0.

- [ ] **Step 6 : Commit** — `chore: garde-fou de taille des fichiers et fonctions (baseline à cliquet)`

### Task 2 : Test d'architecture (règles d'import entre couches)

**Files:**
- Create: `backend/app/services/__init__.py`, `backend/app/repositories/__init__.py`, `backend/app/domain/__init__.py`, `backend/app/integrations/__init__.py` (vides, une docstring d'une ligne sur le rôle de la couche)
- Create: `backend/tests/test_architecture.py`
- Create: `backend/tests/architecture_baseline.txt` (générée, une violation par ligne, triée)

**Interfaces:**
- Produces, dans `test_architecture.py` :
  - `FORBIDDEN: dict[str, tuple[str, ...]]`, clés = préfixe de couche, valeurs = préfixes interdits, recopiés du tableau de la spec :
    - `app.services` : `app.api`, `fastapi`
    - `app.repositories` : `app.api`, `app.services`, `app.integrations`, `fastapi`
    - `app.domain` : `app.api`, `app.services`, `app.repositories`, `app.integrations`, `app.db`, `sqlalchemy.orm`, `fastapi`
    - `app.integrations` : `app.api`, `app.services`, `app.repositories`
    - `app.core` : `app.api`
    - `app.models`, `app.schemas`, `app.db` : `app.api`, `app.services`, `app.repositories`, `app.integrations`
  - Règle spéciale `app.api` : importer un `app.api.X` est une violation, sauf `app.api.deps` et les modules du même package que l'importeur (`app.api.analytics.budget` → `app.api.analytics.utils` autorisé).
  - `imported_modules(path: Path, module: str) -> set[str]` : tous les `Import`/`ImportFrom` de l'AST, **y compris ceux dans les fonctions** ; imports relatifs résolus en absolus ; `from app.api import deps` → `app.api.deps` quand ce sous-module existe.
  - `violations(app_dir: Path) -> set[str]`, au format `app/core/salary.py -> app.api.transactions`, plus `app/repositories/x.py -> commit()` pour tout appel d'attribut `.commit(` dans `repositories/`.

- [ ] **Step 1 : Écrire les tests**

```python
def test_relative_imports_are_resolved(tmp_path):
    write(tmp_path / "app/api/analytics/budget.py", "from .utils import x\nfrom ..transactions import y\n")
    assert imported_modules(tmp_path / "app/api/analytics/budget.py", "app.api.analytics.budget") >= {
        "app.api.analytics.utils", "app.api.transactions"}

def test_repository_commit_is_a_violation(tmp_path):
    write(tmp_path / "app/repositories/r.py", "def f(db):\n    db.commit()\n")
    assert "app/repositories/r.py -> commit()" in violations(tmp_path / "app")

def test_layers_match_baseline():
    app_dir = Path(__file__).parents[1] / "app"
    baseline = set((Path(__file__).parent / "architecture_baseline.txt").read_text().split("\n")) - {""}
    found = violations(app_dir)
    assert found - baseline == set(), "nouvelles violations"
    assert baseline - found == set(), "violations corrigées : les retirer de la baseline"
```

- [ ] **Step 2 : Lancer les tests et constater l'échec** — `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_architecture.py -v` → FAIL.

- [ ] **Step 3 : Implémenter les helpers et générer la baseline** (petit bloc `if __name__ == "__main__":` qui écrit `sorted(violations(...))`). Elle doit au minimum contenir les dépendances inversées connues : `app/core/salary.py -> app.api.transactions`, `app/core/recurring.py -> app.api.transactions`, `app/core/demo.py -> app.api.transactions`, `app/core/notifications.py -> app.api.analytics.{audit,budget,reports}`, `app/core/month_review.py -> app.api.analytics.utils`, `app/core/provisions.py -> app.api.analytics.utils`, `app/api/month_review.py -> app.api.accounts`, `app/api/tax.py -> app.api.analytics.budget`, `app/api/auth.py -> app.api.totp`, `app/api/passkeys.py -> app.api.auth`, `app/api/imports.py -> app.api.transactions`.

- [ ] **Step 4 : Vérifier** — la suite complète passe.

- [ ] **Step 5 : Commit** — `chore: test d'architecture des couches (baseline à cliquet) + squelette services/repositories/domain/integrations`

---

## Phase 1 — Fondations

### Task 3 : Erreurs métier et handler HTTP

**Files:**
- Modify: `backend/app/core/errors.py`
- Modify: `backend/app/main.py` (à côté des `@app.exception_handler` existants, l. 153-180)
- Test: `backend/tests/test_domain_errors.py`

**Interfaces:**
- Produces, dans `app.core.errors` :
  - `class DomainError(Exception)` : attribut de classe `status_code = 400`, `__init__(self, detail: str, code: str | None = None, context: dict | None = None)`
  - `NotFoundError(DomainError)` 404, `BusinessRuleError(DomainError)` 422, `ConflictError(DomainError)` 409
- Produces, dans `app.main` : `async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse`, enregistré via `@app.exception_handler(DomainError)`. Corps `{"detail": exc.detail}` si `code is None`, sinon `{"detail": {"code": …, "detail": …, "context": … or {}}}` (identique à `api_error`).

- [ ] **Step 1 : Écrire les tests** (appel direct du handler avec `Request({"type": "http"})`) :
  - `test_not_found_keeps_plain_detail` : `NotFoundError("Account not found")` → 404, corps `{"detail": "Account not found"}`
  - `test_business_rule_with_code_matches_api_error_shape` : `BusinessRuleError("x", code="invalid_type", context={"a": 1})` → 422, corps `{"detail": {"code": "invalid_type", "detail": "x", "context": {"a": 1}}}`
  - `test_conflict_status` : `ConflictError("dup")` → 409
- [ ] **Step 2 : Lancer et constater l'échec.**
- [ ] **Step 3 : Implémenter.**
- [ ] **Step 4 : Suite complète verte.**
- [ ] **Step 5 : Commit** — `feat(core): erreurs métier DomainError traduites en HTTP`

### Task 4 : Sortir les helpers partagés de soldes vers `services/`

**Files:**
- Create: `backend/app/services/balances.py`, `backend/app/services/accounts.py`
- Modify: `backend/app/api/transactions.py` (retirer `recalculate_running_balances`, l. 18-32), `backend/app/api/accounts.py` (retirer `_get_balance_for_account`, l. 27-49)
- Modify (importeurs) : `core/salary.py`, `core/recurring.py`, `core/demo.py`, `api/categorization_rules.py`, `api/salary.py` (2), `api/imports.py`, `api/month_review.py`, `api/analytics/tax.py`, `tests/test_reconciliation.py`, `tests/test_wrapped.py`, plus tout autre résultat de `grep -rn "recalculate_running_balances\|_get_balance_for_account" backend`
- Modify: `backend/tests/architecture_baseline.txt` (retirer les lignes résolues), `scripts/code_size_baseline.json` si une clé bouge

**Interfaces:**
- Produces : `app.services.balances.recalculate_running_balances(db: Session, account_id: int) -> None` (corps à l'identique, commit compris : la frontière de transaction ne bouge pas dans cette tâche)
- Produces : `app.services.accounts.account_balance(db: Session, account_id: int) -> float` (corps de `_get_balance_for_account` à l'identique, docstring comprise)

- [ ] **Step 1 : Déplacer les deux fonctions à l'identique** et mettre à jour tous les importeurs. Garder les imports locaux là où ils l'étaient (`core/recurring.py:342`, `api/salary.py`).
- [ ] **Step 2 : Vérifier qu'il ne reste aucune référence** — `grep -rn "api.transactions import recalculate\|_get_balance_for_account" backend` → aucun résultat.
- [ ] **Step 3 : Retirer de `architecture_baseline.txt` les lignes qui ne se produisent plus.**
- [ ] **Step 4 : Suite complète verte.**
- [ ] **Step 5 : Commit** — `refactor: recalculate_running_balances et account_balance dans services/`

### Task 5 : Démanteler `api/analytics/utils.py`

**Files:**
- Create: `backend/app/repositories/analytics/__init__.py`, `backend/app/repositories/analytics/common.py`, `backend/app/domain/transactions.py`
- Delete: `backend/app/api/analytics/utils.py`
- Modify : tous les importeurs. Absolus : `core/month_review.py` (5 imports locaux), `core/provisions.py`, `api/transactions.py:135`. Relatifs : `from .utils` dans `api/analytics/*`. Trouver la liste complète avec `grep -rn "analytics.utils\|from \.utils\|from \.\.utils" backend`.

**Interfaces:**
- Produces, dans `app.repositories.analytics.common` (fonctions qui prennent une Session ou construisent une expression SQL) : `NET_AMOUNT`, `category_lines()`, `income_criterion(db)`, `budget_versement_ids(db)`, `opening_balances_eur(db, start, end, rates)`, `savings_account_ids(db)`, `savings_events_by_account(db, account_ids, end_date)`, `savings_total_at(db, account_ids, end_date)`, `ticket_restaurant_account_ids(db)`.
- Produces, dans `app.domain.transactions` (purs) : `net_amount(tx: Transaction) -> float`, `tx_sample(tx: Transaction) -> dict`, `tx_read(tx: Transaction) -> dict`.
- Renommages (le `_` disparaît puisque ces helpers deviennent publics) : `_get_ticket_restaurant_account_ids` → `ticket_restaurant_account_ids`, `_savings_account_ids` → `savings_account_ids`, `_savings_events_by_account` → `savings_events_by_account`, `_savings_total_at` → `savings_total_at`, `_tx_sample` → `tx_sample`, `_tx_read` → `tx_read`.

- [ ] **Step 1 : Écrire `backend/tests/test_domain_transactions.py`** : `test_net_amount_subtracts_reimbursement_offset` (un `Transaction(amount=100.0, reimbursement_offset=30.0)` non persisté → `net_amount(...) == 70.0`).
- [ ] **Step 2 : Le lancer** → FAIL (module absent).
- [ ] **Step 3 : Déplacer à l'identique, renommer, mettre à jour tous les importeurs, supprimer `utils.py`.**
- [ ] **Step 4 : Vérifier** — `grep -rn "analytics.utils\|from \.utils" backend` → aucun résultat ; suite complète verte ; baseline d'architecture allégée.
- [ ] **Step 5 : Commit** — `refactor: helpers analytics répartis entre repositories/analytics et domain`

### Task 6 : Ne plus jamais appeler une fonction de route

**Files:**
- Create: `backend/app/services/analytics/__init__.py`, `backend/app/services/analytics/budget.py`, `backend/app/services/analytics/cashflow.py`, `backend/app/services/audit.py`, `backend/app/services/tax.py`
- Modify: `api/analytics/budget.py` (routes `/budget` l. 74, `/budget/alerts` l. 629 ; `compute_resilience` l. 592), `api/analytics/audit.py` (`/actions` l. 525), `api/analytics/reports.py` (`/cashflow-projection` l. 80), `api/analytics/tax.py` (vidé de ses helpers, conserve ses éventuelles routes), `api/tax.py`, `api/month_review.py`, `core/notifications.py` (l. 189 et 260-261)
- Test: `backend/tests/test_notifications.py` (ajout)

**Interfaces:**
- Produces (corps de route déplacés **à l'identique**, sauf `HTTPException(404)` → `NotFoundError(detail)` et `HTTPException(422)` → `BusinessRuleError(detail)` avec le même texte) :
  - `app.services.analytics.budget` : `async def compute_budget(db: Session, month: int | None, year: int | None, account_id: int | None) -> dict` ; `async def compute_budget_alerts(db: Session, year: int, month: int, account_id: int | None)` (même type de retour que la route actuelle) ; `async def compute_resilience(db: Session, year: int, month: int, window: int = RESILIENCE_WINDOW_MONTHS) -> dict` (déplacée avec sa constante)
  - `app.services.audit` : `async def compute_action_center(db: Session) -> ActionCenterResponse`
  - `app.services.analytics.cashflow` : `async def compute_cashflow_projection(db: Session, days: int = 30, account_id: int | None = None) -> CashflowProjection`
  - `app.services.tax` : `load_tax_settings`, `save_tax_settings`, `build_overview`, `build_annual_report` et leurs helpers privés, signatures inchangées
- Chaque route concernée devient un appel d'une ligne à son service. `core/notifications.py`, `api/month_review.py` et `api/tax.py` appellent les services.
- Baseline de taille : renommer `…/api/analytics/budget.py::budget_analytics` → `backend/app/services/analytics/budget.py::compute_budget` (même valeur), et de même pour `get_action_center` → `compute_action_center`, etc.

- [ ] **Step 1 : Écrire le test** `test_digest_body_contains_budget_and_actions_lines` dans `test_notifications.py` : base avec un compte courant et une Sortie du mois, `await _digest_body(db_session, datetime.now())` contient `"Ce mois-ci :"` et `"Centre d'Actions :"`. Il doit passer **avant** le refactoring (test de caractérisation) : le lancer pour le confirmer.
- [ ] **Step 2 : Déplacer les corps, transformer les routes en wrappers, mettre à jour les appelants.**
- [ ] **Step 3 : Vérifier** — `grep -rn "from app.api" backend/app/core backend/app/services` → aucun résultat ; suite complète verte (dont le test du step 1) ; lignes correspondantes retirées de la baseline d'architecture.
- [ ] **Step 4 : Commit** — `refactor: budget, centre d'actions, cashflow et fiscalité appelés via services/`

### Task 7 : Supprimer les imports entre routers d'authentification

**Files:**
- Modify: `backend/app/core/login_rate_limit.py`, `backend/app/core/totp.py`, `backend/app/api/auth.py`, `backend/app/api/totp.py`, `backend/app/api/passkeys.py`, `backend/tests/conftest.py`, et les tests qui importent `login_rate_limiter` / `totp_rate_limiter`

**Interfaces:**
- Produces, dans `app.core.login_rate_limit` : les instances `login_rate_limiter` et `totp_rate_limiter` (mêmes paramètres qu'aujourd'hui) et `client_key(request: Request, username: str) -> str` (ex-`api.auth._client_key`)
- Produces, dans `app.core.totp` : `is_enabled(db: Session) -> bool` et `create_mfa_token(username: str) -> str` (ex-`api.totp`)

- [ ] **Step 1 : Déplacer à l'identique, mettre à jour les importeurs et le `conftest.py`.**
- [ ] **Step 2 : Vérifier** — `grep -rn "from app.api.\(auth\|totp\) import" backend` → aucun résultat ; suite complète verte (`test_auth.py`, `test_passkeys.py`, `test_totp*.py`) ; baseline d'architecture allégée.
- [ ] **Step 3 : Commit** — `refactor(auth): rate limiters et helpers MFA dans core/`

### Task 8 : `accounts`, le domaine modèle de bout en bout

**Files:**
- Create: `backend/app/repositories/accounts.py`
- Modify: `backend/app/services/accounts.py`, `backend/app/api/accounts.py`
- Test: `backend/tests/test_accounts_service.py`
- Modify: `ARCHITECTURE.md` (nouvelle section « Couches » + arborescence), `backend/CLAUDE.md` (« Structure et cycle de vie », « Règles de code »), `.claude/skills/numera-backend/SKILL.md` (procédure « ajouter un endpoint » = router + service + repository + tests), `CLAUDE.md` racine (section Architecture/Backend)

**Interfaces:**
- Consumes : `account_balance` (tâche 4), `NotFoundError` / `BusinessRuleError` (tâche 3)
- Produces, dans `app.repositories.accounts` : `list_all(db) -> list[Account]` (tri par id), `get(db, account_id: int) -> Account | None`, `latest_snapshot(db, account_id: int) -> BalanceSnapshot | None`, `latest_transaction(db, account_id: int) -> Transaction | None`, plus les requêtes qu'utilise `reconcile`, toutes sans `commit`
- Produces, dans `app.services.accounts` : `list_accounts(db) -> list[Account]` (attribut `balance` renseigné), `get_account(db, account_id) -> Account` (lève `NotFoundError`), `create_account(db, payload: AccountCreate) -> Account`, `update_account(db, account_id, payload: AccountUpdate) -> Account`, `verify_account(db, account_id) -> Account`, `reconcile_account(db, account_id, payload: ReconcileRequest) -> ReconcileResult`, `archive_account(db, account_id) -> Account`. `account_balance` passe par le repository. Les services font le `commit`.
- `api/accounts.py` : chaque route se limite à appeler un service et à renvoyer son résultat (≤ 10 lignes), sans import de `models` ni `db.query`.

- [ ] **Step 1 : Écrire les tests de service** (fixture `db_session`) :
  - `test_account_balance_prefers_snapshot_newer_than_last_transaction`
  - `test_account_balance_falls_back_to_last_running_balance`
  - `test_get_account_unknown_raises_not_found` (`pytest.raises(NotFoundError)`)
  - `test_create_account_rejects_unknown_type` : même exception, même message que ce que renvoie la route aujourd'hui (le lire dans `api/accounts.py:70`)
- [ ] **Step 2 : Les lancer** → FAIL.
- [ ] **Step 3 : Implémenter repository et services, amincir le router.**
- [ ] **Step 4 : Vérifier** — suite complète verte (`test_account_type.py`, `test_reconciliation.py`, `test_archiving.py` inchangés) ; `grep -n "db.query\|commit" backend/app/api/accounts.py` → aucun résultat.
- [ ] **Step 5 : Documenter les conventions** dans les quatre fichiers listés. Les règles viennent de la spec : tableau des couches, plafonds, baselines à cliquet, erreurs métier.
- [ ] **Step 6 : Commit** — `refactor(accounts): domaine modèle router/service/repository + conventions documentées`

---

## Phases suivantes (un plan détaillé par phase, écrit à son ouverture)

**Recette commune, pour chaque domaine :**
1. Tests de caractérisation d'abord, s'il manque une couverture HTTP sur le comportement déplacé.
2. Requêtes → `repositories/<domaine>.py` ; règles et orchestration → `services/<domaine>.py` ; calculs purs → `domain/<domaine>.py` ; appels externes → `integrations/`.
3. Router aminci comme `accounts`.
4. Les fichiers repassent sous les plafonds : retirer les entrées des deux baselines.
5. Docs dans le même commit.

### Phase 2 — Domaines d'écriture (terminée le 28/10/2026)
Plan détaillé : `docs/superpowers/plans/2026-10-28-phase-2-domaines-ecriture.md` (18 tâches). Tâche 1 : le dossier `api/` devient `controllers/` (demande de l'utilisateur). Périmètre : routers d'écriture côté budget et administration, et les modules `core/` qui leur appartiennent (`transfers`, `loans`, `provisions`, `reimbursements`, `splits`, `recurring`, `finance`, `salary`, `work_time`, `month_review`, `reconciliation`, `demo`, `seeds`, `notifications`, `currency`, `logos`, `backup`). Le passage de `recalculate_running_balances` en `flush` y est traité (tâche 15). Les domaines d'écriture côté investissement sont reportés en phase 4.

### Phase 3 — Analytics
`services/analytics/` + `repositories/analytics/` + `domain/` ; plus aucune fonction > 80 lignes.
- `budget` : `compute_budget` découpé en revenus / dépenses / enveloppes / résilience.
- Centre d'Actions : `services/audit/rules/<règle>.py`, chaque règle exposant `def detect(ctx: AuditContext) -> list[ActionItem]`, et un registre qui les agrège (`docs/ACTION_CENTER.md` mis à jour).
- `investments.py` → `summary`, `performance`, `allocation`, `projections` (forecast, FIRE, simulation).
- Puis `metrics`, `reports`, `insights`, `wrapped`, `diversity`, `subscriptions`, `dividends`.
Le router `controllers/analytics/` garde ses chemins et son package.

### Phase 4 — Portefeuille
Routers `investment_transactions`, `holdings`, `etf_profiles`, `market` (reportés de la phase 2) ; `core/seeds_etf.py`. `core/portfolio.py` → `domain/performance.py` (`xirr`, `twr`), `services/portfolio/` (`PriceBook`, `FxBook`, `cash_events`, `compute_portfolio` découpé par étape), puis `core/holdings.py`, `core/etf_analyzer.py`.

### Phase 5 — Frontend
Ordre par taille : `AccountDetail` (2 773), `RecurringTransactions` (1 548), `WealthSimulator` (1 169), `Accounts` (1 057), `Audit` (1 030), `Investments`, `Savings`, `HoldingsTable`, `OverviewTab`, `PointZeroModal`, `Calendar`, `MerchantsTab`, `CategoriesTab`, `Omnibox`, `Tax`, `SalaryManager`, `ImportFlow`.
Cible : `pages/<Page>/index.tsx` (composition), un composant par section et par dialogue, `use<Page>Data.ts` pour le chargement et l'état, `lib/api/<domaine>.ts` pour les appels typés. Vérification : `npm run build` vert, plus un contrôle manuel (thème sombre, mode confidentialité, mobile 375 px) via l'aperçu navigateur.

### Phase 6 — Nettoyage et durcissement
Les deux baselines sont vides. `FORBIDDEN["app.core"]` est durci (core n'importe plus que core, models, db). `core/errors.api_error` est remplacé par les `DomainError`. Relecture finale de `ARCHITECTURE.md`, des `CLAUDE.md` et des skills.
