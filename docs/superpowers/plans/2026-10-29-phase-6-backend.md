# Phase 6 (backend) — Regroupement par domaine et durcissement : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ranger `controllers/`, `services/` et `repositories/` en sous-packages par domaine (`budget/`, `comptes/`, `investissement/`, `analytics/`, `audit/`, `systeme/`), durcir le test d'architecture (frontières entre domaines de controllers, `core/` n'importe que `core`, `models`, `db`), supprimer `core/errors.api_error`, et remettre la documentation à jour. **Aucun changement de code** hors chemins d'import.

**Architecture:** Renommage pur, groupe de domaines par groupe de domaines, par un script de réécriture déterministe (`git mv` puis réécriture des importeurs) ; `main` vert après chaque commit. Puis deux petites tâches de durcissement et une tâche de documentation.

**Tech Stack:** Python 3.11, pytest, FastAPI, `git mv`.

**Spec:** `docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md` · plan maître : `docs/superpowers/plans/2026-10-28-architecture-en-couches.md` (§ Phase 6) · conventions et pièges 1 à 9 : section 0 de `docs/superpowers/plans/2026-10-28-phase-3-analytics.md` · pièges 10 à 15 : `docs/superpowers/plans/2026-10-29-phase-4-portefeuille.md`.

---

## 0. Reprendre ce plan dans une nouvelle conversation

```text
On reprend la phase 6 (backend) de la migration de Numera vers une architecture en couches.
Lis docs/superpowers/plans/2026-10-29-phase-6-backend.md (en entier), la section 0 du plan de la phase 3,
puis le ledger .superpowers/sdd/2026-10-29-phase-6-backend/progress.md (une tâche « complete » n'est pas refaite).
Exécute la suite toi-même (skill superpowers:executing-plans). Commits directement sur main, sans push.
```

- État au départ (commit `a4778c2`) : phases 0 à 4 terminées ; ~910 tests ; `tests/architecture_baseline.txt` vide ; `scripts/code_size_baseline.json` = 21 entrées, **toutes frontend** (aucune clé backend à renommer).
- Ledger : `.superpowers/sdd/2026-10-29-phase-6-backend/progress.md` (ignoré par git), `Task N: complete (…)` via `task-done`, `Task N: Ruling: <décision> — <pourquoi> — <coût si faux>`.

### Pièges propres à la phase 6

16. **Forme `from app.services import accounts as service`** : 60 importeurs n'écrivent pas le chemin pointé complet ; un remplacement de `app.services.accounts` ne les voit pas. Le script les traite à part (`from app.services.comptes import accounts as service`).
17. **Chaînes synthétiques de `tests/test_architecture.py`** (faux modules `app/controllers/month_review.py`, `app.controllers.accounts`) : exclues de la réécriture (piège 6).
18. **Plans historiques** (`docs/superpowers/`) : jamais réécrits ; ils décrivent l'état de leur époque.
19. **Chemin en doc sans préfixe** (`services/wealth.py`, `services.wealth::account_values`) : le script réécrit `L/name` et `L.name` dans les `.md` hors `docs/superpowers/` ; relecture manuelle en tâche 7 (`grep` des anciens chemins).
20. **Patch par chaîne** (`monkeypatch.setattr("app.services.x.f", …)`) : couvert par la réécriture pointée ; un oubli fait échouer bruyamment (`block_network`).

## Répartition

Les noms de module ne changent pas ; seul le dossier parent change. `controllers/deps.py` reste à la racine (partagé). `analytics/` et `audit/` ne bougent pas (y compris `controllers/analytics/{audit,portfolio,dividends,diversity,investments}.py`, montés sous `/analytics`). `domain/` et `integrations/` restent plats.

| Domaine | `controllers/` | `services/` | `repositories/` |
|---|---|---|---|
| `systeme/` | auth, totp, passkeys, admin, notifications, logos, health | admin, notifications, logos, seeds, demo/ | admin |
| `comptes/` | accounts, balance_snapshots, loans, financial_events | accounts, balance_snapshots, reconciliation, loans, wealth, financial_events | accounts, balance_snapshots, reconciliation, loans, financial_events |
| `investissement/` | investment_transactions, holdings, etf_profiles, market, tax | investment_transactions, holdings/, etf_profiles, market/, tax, dividends, portfolio/ | investment_transactions, holdings, etf_profiles, portfolio, security_prices |
| `budget/` | transactions, categories, categorization_rules, merchants, tags, imports, exports, recurring_transactions, salary, transfer_rules, reimbursements, provisions, savings_goals, month_review | transactions, transaction_writes, transaction_links, splits, balances, categories, categorization_rules, merchants, tags, imports, exports, recurring, recurring_transactions, salary, salary_generation, work_time, transfer_rules, transfers, reimbursements, provisions, savings_goals, month_review, budget_period, subscription_prices | transactions, categories, categorization_rules, merchants, tags, imports, exports, recurring, salary, transfer_rules, transfers, reimbursements, provisions, savings_goals, month_review, budget_period |

Chaque nouveau package reçoit un `__init__.py` d'une ligne (docstring du domaine), identique dans les trois couches, sans import.

## Global Constraints

- **Zéro changement de code** : seules les lignes d'import, les chaînes de chemin de module et les chemins cités en doc changent. `git diff -M --stat` montre des renommages ; `git diff -M` ne contient que des lignes d'import/chemin.
- `tests/test_analytics_snapshots.py` et `tests/test_portfolio_snapshots.py` passent à l'identique ; les instantanés ne sont **jamais** régénérés.
- `main` vert après chaque commit : suite complète, `make check-size`, `tests/architecture_baseline.txt` vide.
- Sans ré-export, sans module de compatibilité ; `grep` de l'ancien chemin vide hors `docs/superpowers/`.
- Mêmes routes (`protected_routers` de `main.py` inchangé dans son contenu, imports repointés), OpenAPI identique.
- Commit par tâche, en français, sur `main`, terminé par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- **Ordre des routes** : l'ordre d'inclusion dans `main.py` détermine la résolution des chemins ambigus ; vérifié par `test_openapi_unchanged` (chemins + méthodes avant/après, tâche 1).
- **Patch de test devenu sans effet** (piège 20) : suite complète au premier plan.
- **Import circulaire révélé par un nouveau `__init__.py`** : les `__init__` de domaine restent vides de code.
- **Doc pointant vers un chemin disparu** : tâche 7, `grep` des anciens chemins.
- **Script de réécriture trop large** (un `services/x` frontend, un nom de variable) : relire `git diff -M` de chaque commit ; le script ne touche que `backend/`, `scripts/` et les `.md` listés.

---

### Task 1 : Script de réécriture et domaine `systeme/`

**Files:**
- Create: `.superpowers/sdd/2026-10-29-phase-6-backend/regroup.py` (outil, non versionné), `app/{controllers,services,repositories}/systeme/__init__.py`
- Move: modules `systeme` du tableau
- Modify: tous les importeurs (`app/`, `tests/`, `scripts/`), `.md` de doc hors `docs/superpowers/`
- Test: `backend/tests/test_openapi_routes.py` (nouveau)

**Interfaces:**
- `regroup.py <domaine> <couche>:<nom> …` : pour chaque `couche:nom`, `git mv app/<couche>/<nom>[.py] app/<couche>/<domaine>/`, puis réécrit dans `backend/**/*.py` (hors `venv`, `tests/test_architecture.py`), `scripts/*.py` :
  1. `from app.<couche> import <nom>` → `from app.<couche>.<domaine> import <nom>` (échoue si une ligne importe plusieurs noms dont un déplacé) ;
  2. `(?<![\w.])app\.<couche>\.<nom>(?!\w)` → `app.<couche>.<domaine>.<nom>` ;
  et dans les `.md` (`*.md` racine, `backend/*.md`, `docs/*.md`, `.claude/skills/**/*.md`, `mcp-server/README.md`, `frontend/src/CLAUDE.md`) en plus : `(?<![\w/])((?:backend/)?(?:app/)?)<couche>/<nom>(?=[./\s`'"),:;|]|$)` et `(?<![\w.])<couche>\.<nom>(?!\w)`.
- `tests/test_openapi_routes.py::test_openapi_routes_unchanged` : ensemble `(méthode, chemin)` de `app.openapi()` comparé à `tests/snapshots/openapi_routes.json`, généré une fois **avant** le premier déplacement (même convention `UPDATE_SNAPSHOTS=1` que les instantanés).

- [ ] **Step 1 : Test des routes** : écrire `test_openapi_routes_unchanged`, générer le fichier sur `a4778c2`, relancer → PASS.
- [ ] **Step 2 : Écrire `regroup.py`**, le lancer pour `systeme` ; `git diff -M --stat` → renommages + importeurs.
- [ ] **Step 3 : Vérifier** : `PYTHONPATH=. python3.11 -m pytest tests/test_architecture.py tests/test_openapi_routes.py tests/test_analytics_snapshots.py tests/test_portfolio_snapshots.py -q` PASS ; suite complète au premier plan ; `make check-size` ; `grep -rnE "app\.(controllers|services|repositories)\.(auth|totp|passkeys|admin|notifications|logos|health|seeds|demo)\b" backend scripts` vide.
- [ ] **Step 4 : Commit** — `refactor(systeme): controllers, services et repositories système regroupés dans systeme/`

### Task 2 : Domaine `comptes/`

**Files:** Move les modules `comptes` du tableau ; Create `app/{controllers,services,repositories}/comptes/__init__.py` ; Modify importeurs.

- [ ] **Step 1 : `regroup.py comptes …`**
- [ ] **Step 2 : Vérifier** (même commande qu'en tâche 1, `grep` des noms du groupe vide).
- [ ] **Step 3 : Commit** — `refactor(comptes): comptes, relevés, rapprochement, crédits et patrimoine regroupés dans comptes/`

### Task 3 : Domaine `investissement/`

**Files:** Move les modules `investissement` (dont les packages `services/holdings/`, `services/market/`, `services/portfolio/`) ; Create les `__init__.py` ; Modify importeurs (dont les patchs réseau des pièges 10-11 : `yahoo_finance` ne bouge pas, `quotes._QUOTES_CACHE` suit son module).

- [ ] **Step 1 : `regroup.py investissement …`**
- [ ] **Step 2 : Vérifier** (idem).
- [ ] **Step 3 : Commit** — `refactor(investissement): opérations, positions, ETF, marché, fiscalité et portefeuille regroupés dans investissement/`

### Task 4 : Domaine `budget/`

**Files:** Move les modules `budget` ; Create les `__init__.py` ; Modify importeurs.

- [ ] **Step 1 : `regroup.py budget …`** ; après coup, `ls app/controllers app/services app/repositories` → seulement les packages de domaine, `deps.py` et les `__init__.py`.
- [ ] **Step 2 : Vérifier** (idem).
- [ ] **Step 3 : Commit** — `refactor(budget): transactions, catégories, imports, récurrences, salaire et épargne regroupés dans budget/`

### Task 5 : Test d'architecture durci

**Files:** Modify `backend/tests/test_architecture.py`.

**Interfaces:**
- `_controllers_violation(module, imported) -> bool` : autorisé si `imported` est `app.controllers.deps`, le module lui-même, ou dans le même package de domaine `app.controllers.<domaine>` (3 premiers segments) ; un module directement sous `app.controllers` n'a pas de domaine.
- `FORBIDDEN["app.core"] = ("app.controllers", "app.services", "app.repositories", "app.domain", "app.integrations", "app.schemas")` (core n'importe que `core`, `models`, `db` dans `app`).

- [ ] **Step 1 : Tests** : `test_controllers_may_import_deps_and_own_domain_only` (`controllers/budget/month_review.py` important `app.controllers.comptes.accounts` → violation ; `app.controllers.budget.transactions` et `app.controllers.deps` → permis ; `controllers/analytics/budget.py` → `.utils` permis) ; `test_core_imports_only_core_models_db` (`app/core/x.py` important `app.services.s` et `app.schemas.y` → violations ; `app.models.m`, `app.db.session`, `app.core.config` → permis). → FAIL.
- [ ] **Step 2 : Implémenter** ; `test_layers_match_baseline` PASS avec baseline vide.
- [ ] **Step 3 : Commit** — `test(architecture): frontières entre domaines de controllers et core limité à core, models, db`

### Task 6 : Suppression de `api_error`

**Files:** Modify `backend/app/core/errors.py` (fonction + import `fastapi` + docstring de `DomainError` : « avec, `{"code","detail","context"}` »), `backend/tests/test_domain_errors.py` (renommer `test_business_rule_with_code_matches_api_error_shape` → `…_structured_shape`, assertions inchangées), `backend/CLAUDE.md` (phrase « Routers non migrés : `api_error`… » → `HTTPException` réservée à 401/403/413/429 dans `controllers/`), `ARCHITECTURE.md` (« même corps qu'`api_error` » → corps `{"detail"}` ou `{"detail": {"code","detail","context"}}`).

- [ ] **Step 1 :** `grep -rn api_error backend ARCHITECTURE.md CLAUDE.md .claude` → seules les lignes ci-dessus ; éditer.
- [ ] **Step 2 :** `tests/test_domain_errors.py` + `tests/test_architecture.py` PASS ; suite complète.
- [ ] **Step 3 : Commit** — `refactor(core): suppression de api_error, remplacé par les DomainError`

### Task 7 : Relecture de la documentation

**Files:** `ARCHITECTURE.md` (arborescence backend, § Couches backend : sous-packages par domaine, règle entre domaines de controllers, `core/` durci, carte des domaines), `CLAUDE.md` (§ Architecture backend : chemins), `backend/CLAUDE.md`, `.claude/skills/numera-*/SKILL.md` (et références), `docs/ACTION_CENTER.md`, `docs/BACKEND.md`, `backend/LOGGING.md`, `README.md`, `mcp-server/README.md` si concernés ; plan maître (§ Phase 6 : partie backend terminée le 29/10/2026 ; baselines d'architecture vide ; vider la baseline de taille, 21 entrées frontend, attend la phase 5).

- [ ] **Step 1 :** `grep -rnE "(controllers|services|repositories)/(<tous les anciens noms>)" --include='*.md' . | grep -v docs/superpowers | grep -v node_modules` → vide ; idem pour la forme pointée.
- [ ] **Step 2 :** relire et corriger à la main les passages descriptifs (arborescence, § Couches, `protected_routers`).
- [ ] **Step 3 :** vérification finale : suite complète, `make check-size`, `cd frontend && npm run build`, baseline d'architecture vide, `git diff a4778c2 -- backend/tests/snapshots` vide (hors `openapi_routes.json` ajouté).
- [ ] **Step 4 : Commit** — `docs: phase 6 backend terminée (regroupement par domaine, durcissement)`
