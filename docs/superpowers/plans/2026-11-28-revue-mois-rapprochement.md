# Revue de mois : rapprochement des comptes — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** Dans l'étape « Comptes » de la revue de mois, on tape le solde du relevé de chaque compte bancaire, à la date de fin de mois. Numera valide le compte ou explique l'écart. Les comptes qui n'ont pas bougé se valident en un clic, et les placements sont traités à part.

**Architecture :** Le backend enrichit `_accounts_step` avec, pour chaque compte, un groupe, une date de relevé et le solde de Numera à cette date. Ces deux derniers sont calculés en une seule requête par `latest_balances_by_account`. Il ajoute aussi une route `POST /month-review/accounts/confirm-unchanged`. Le frontend réutilise `POST /accounts/{id}/reconcile`, avec un composant d'affichage des causes probables partagé avec `ReconcileDialog`.

**Stack :** FastAPI, SQLAlchemy 2, Pydantic v2, pytest · React 19, TypeScript, Tailwind, Vitest, MSW, i18next.

**Spec :** `docs/superpowers/specs/2026-11-28-revue-mois-rapprochement-design.md`

## Contraintes globales

- Le travail se fait sur une branche `feat/revue-rapprochement` partie de `main`, dans un worktree. La branche `feat/investissements-onglets` contient du travail non commité et ne doit pas être touchée.
- Méthode TDD côté backend : test rouge avant le code (skill `numera-tdd`).
- Pas de requête SQL dans une boucle sur les comptes.
- Bornes exclusives : la fin d'un jour `d` s'écrit `datetime.combine(d + timedelta(days=1), time.min)`, et les comparaisons utilisent `< end`.
- L'horloge passe par `core/time.py` (`today_local()`), jamais par `datetime.now()`.
- Chaque nouveau texte d'interface va dans `fr`, `en` et `es` (`locales/*/month.json`), en tutoyant.
- Les fichiers font au plus 350 lignes côté frontend, au plus 400 lignes et 80 lignes par fonction côté backend.
- Toute route ou tout schéma modifié est suivi de `make api-contract`, d'une mise à jour de `backend/tests/snapshots/openapi_routes.json` et d'`ARCHITECTURE.md`.
- La route ajoutée est une écriture : aucun outil MCP.

## Points d'attention pour la revue

1. **Mois en cours ouvert dans la revue** : la date du relevé est aujourd'hui, et non le 30 ou le 31 d'un mois futur (test en tâche 1).
2. **Compte sans aucune transaction** : il va dans le groupe `unchanged`, avec un solde de relevé à 0, sans erreur (test en tâche 1).
3. **Transaction datée après la date du relevé** (à venir, ou déjà dans le mois suivant) : elle n'entre ni dans le solde ni dans le critère « a bougé » (test en tâche 1).
4. **Placement `assurance_vie` ou `investissement`** : il est toujours dans le groupe `market` et jamais validé par `confirm-unchanged` (test en tâche 2).
5. **Saisie avec une virgule (« 1 248,30 »)** : elle est acceptée par le champ du relevé (test en tâche 4).

---

### Tâche 1 : groupe, date et solde du relevé dans l'étape Comptes

**Fichiers :**
- Modifier : `backend/app/schemas/month_review.py` (`AccountCheck`)
- Modifier : `backend/app/services/budget/month_review.py` (`_accounts_step`, nouvelle fonction `statement_date`)
- Test : `backend/tests/budget/test_month_review.py`

**Interfaces :**
- Produit : `AccountCheck.group: Literal["reconcile", "unchanged", "market"]`, `AccountCheck.statement_date: date`, `AccountCheck.statement_balance: float | None` (`None` pour `market`). `AccountsStep` reste inchangé par ailleurs.
- Produit : `statement_date(year: int, month: int) -> date` dans `services/budget/month_review.py`, qui renvoie le dernier jour calendaire du mois, plafonné à `today_local()`.
- Consomme : `repositories.comptes.balances.latest_balances_by_account(db, ids, before=end)` → `{id: BalanceRow(date, running_balance)}`.

Règle du groupe : `market` si `acc.type in ("investissement", "assurance_vie")`. Sinon `unchanged` si le compte n'a aucune transaction avant la fin du jour du relevé, ou si la dernière date `< acc.last_verified_at`. Sinon `reconcile`.

- [ ] **Étape 1 : écrire les tests qui échouent** (avec `recalculate_running_balances(db, acc.id)` puis `db.commit()` après les `_tx`, pour que les soldes soient justes)

```python
def test_accounts_step_gives_statement_balance_at_calendar_month_end(client, db_session):
    acc = _courant(db_session, last_verified_at=datetime(2025, 9, 1))
    _tx(db_session, acc, "Entree", 1000.0, datetime(2025, 10, 5))
    _tx(db_session, acc, "Sortie", 50.0, datetime(2025, 11, 2))  # après le relevé
    recalculate_running_balances(db_session, acc.id); db_session.commit()
    item = client.get("/month-review", params=PARAMS).json()["accounts"]["accounts"][0]
    assert item["statement_date"] == "2025-10-31"
    assert item["statement_balance"] == 1000.0
    assert item["group"] == "reconcile"

def test_account_without_movement_since_verification_is_unchanged(client, db_session):
    acc = _courant(db_session, last_verified_at=datetime(2025, 10, 10))
    _tx(db_session, acc, "Entree", 500.0, datetime(2025, 10, 3))
    empty = Account(name="Vide", type="epargne", currency="EUR", active=True); db_session.add(empty); db_session.commit()
    recalculate_running_balances(db_session, acc.id); db_session.commit()
    groups = {a["name"]: (a["group"], a["statement_balance"]) for a in client.get("/month-review", params=PARAMS).json()["accounts"]["accounts"]}
    assert groups == {"Principal": ("unchanged", 500.0), "Vide": ("unchanged", 0.0)}

def test_market_accounts_have_no_statement_balance(client, db_session):
    for type_ in ("investissement", "assurance_vie"):
        db_session.add(Account(name=type_, type=type_, currency="EUR", active=True))
    db_session.commit()
    items = client.get("/month-review", params=PARAMS).json()["accounts"]["accounts"]
    assert {(a["group"], a["statement_balance"]) for a in items} == {("market", None)}

def test_statement_date_is_capped_at_today(monkeypatch):
    monkeypatch.setattr(month_review_service, "today_local", lambda: date(2025, 10, 12))
    assert month_review_service.statement_date(2025, 10) == date(2025, 10, 12)
    assert month_review_service.statement_date(2025, 2) == date(2025, 2, 28)
```

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent**
Commande : `cd backend && PYTHONPATH=. python3.11 -m pytest tests/budget/test_month_review.py -k "statement or unchanged or market" -v`
Résultat attendu : FAIL (`KeyError: 'statement_date'`, ou fonction introuvable).

- [ ] **Étape 3 : implémenter** `statement_date` et les trois champs dans `_accounts_step`. Utiliser `calendar.monthrange` pour le dernier jour du mois et un seul appel à `latest_balances_by_account` pour tous les comptes non `market`. `_accounts_step` prend désormais `year, month` en plus de `end`, et `_build_review` lui passe les deux. `verified_since_month_end` et son `reference` restent inchangés.

- [ ] **Étape 4 : lancer tout le fichier et vérifier qu'il passe**
Commande : `cd backend && PYTHONPATH=. python3.11 -m pytest tests/budget/ -q`
Résultat attendu : PASS. Les tests existants doivent rester verts, en particulier `test_review_accounts_step_flags_stale_accounts`.

- [ ] **Étape 5 : commit** `feat(revue): solde du relevé et groupe de chaque compte dans la revue de mois`

### Tâche 2 : route « Rien n'a bougé : tout valider »

**Fichiers :**
- Modifier : `backend/app/schemas/month_review.py` (nouveau `MonthRef { year: int (2000–2200), month: int (1–12) }`, ou réutiliser la validation de `CloseRequest`)
- Modifier : `backend/app/services/budget/month_review.py` (`confirm_unchanged_accounts`)
- Modifier : `backend/app/controllers/budget/month_review.py`
- Modifier : `backend/tests/snapshots/openapi_routes.json`, `ARCHITECTURE.md` (routes `/month-review`), `frontend/src/lib/api/generated/*` (`make api-contract`)
- Test : `backend/tests/budget/test_month_review.py`

**Interfaces :**
- Produit : `POST /month-review/accounts/confirm-unchanged`, corps `{year, month}`, réponse `MonthReviewRead` (la revue recalculée).
- Produit : `async def confirm_unchanged_accounts(db: Session, year: int, month: int) -> dict[str, Any]`. Elle pose `last_verified_at = utcnow_naive()` sur les comptes du groupe `unchanged` de la tâche 1 (même calcul, sans le dupliquer : extraire une fonction `_account_groups(db, accounts, day) -> dict[int, str]` utilisée par les deux), fait un seul `commit`, puis renvoie `_build_review`.

- [ ] **Étape 1 : écrire les tests qui échouent**

```python
def test_confirm_unchanged_verifies_only_unchanged_bank_accounts(client, db_session):
    still = _courant(db_session, last_verified_at=datetime(2025, 10, 10))
    moved = Account(name="Bougé", type="courant", currency="EUR", active=True, last_verified_at=datetime(2025, 9, 1))
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True, last_verified_at=datetime(2025, 9, 1))
    db_session.add_all([moved, pea]); db_session.commit()
    _tx(db_session, moved, "Sortie", 10.0, datetime(2025, 10, 20))
    res = client.post("/month-review/accounts/confirm-unchanged", json=PARAMS)
    assert res.status_code == 200
    verified = {a["name"]: a["verified_since_month_end"] for a in res.json()["accounts"]["accounts"]}
    assert verified == {"Principal": True, "Bougé": False, "PEA": False}
    db_session.expire_all()
    assert db_session.get(Account, pea.id).last_verified_at == datetime(2025, 9, 1)

def test_confirm_unchanged_rejects_invalid_month(client):
    assert client.post("/month-review/accounts/confirm-unchanged", json={"year": 2025, "month": 13}).status_code == 422
```

- [ ] **Étape 2 : lancer les tests et vérifier qu'ils échouent** (`-k confirm_unchanged`). Résultat attendu : 404 ou 405.
- [ ] **Étape 3 : implémenter.** Le service suit le modèle de `close_month`, et le controller l'appelle par `run_async`, comme les routes voisines.
- [ ] **Étape 4 :** `make api-contract`, ajouter la route à `openapi_routes.json` et à `ARCHITECTURE.md`, puis `cd backend && PYTHONPATH=. python3.11 -m pytest tests/budget tests/garde_fous -q`. Résultat attendu : PASS.
- [ ] **Étape 5 : commit** `feat(revue): valider en un clic les comptes qui n'ont pas bougé`

### Tâche 3 : extraire l'affichage des causes probables

**Fichiers :**
- Créer : `frontend/src/components/accounts/ReconcileHints.tsx`
- Modifier : `frontend/src/components/accounts/ReconcileDialog.tsx` (utilise le nouveau composant ; types `ReconcileHint` et `ReconcileResult` exportés depuis `ReconcileHints.tsx`)
- Test : `frontend/src/test/components/accounts/ReconcileDialog.test.tsx` doit rester vert sans modification

**Interfaces :**
- Produit : `export function ReconcileHints({ hints, currency }: { hints: ReconcileHint[]; currency: string })`, déplacé à l'identique depuis `ReconcileDialog`, icônes `HINT_ICONS` comprises. Produit aussi `export type ReconcileResult`.

- [ ] **Étape 1 :** déplacer le bloc `result.hints.map(...)` et `HINT_ICONS` dans `ReconcileHints.tsx`, sans changement de rendu.
- [ ] **Étape 2 :** `cd frontend && npx vitest run src/test/components/accounts` doit passer, puis `npm run typecheck && npm run knip`.
- [ ] **Étape 3 : commit** `refactor(comptes): composant partagé pour les causes d'un écart de rapprochement`

### Tâche 4 : nouvelle étape Comptes en trois blocs

**Fichiers :**
- Modifier : `frontend/src/components/month-review/AccountsStep.tsx` (composition des trois blocs). Si le fichier dépasse 350 lignes, le transformer en dossier `AccountsStep/` avec `index.tsx`, `ReconcileRow.tsx`, `UnchangedBlock.tsx` et `MarketBlock.tsx`.
- Modifier : `frontend/src/pages/MonthReview.tsx` (passe `year`, `month` et un `onReview(data)` à `AccountsStep`)
- Modifier : `frontend/src/lib/api/monthReview.ts` (`postMonthReviewAccountsConfirmUnchanged(body)`), le tableau de `describeApiCases` du test API correspondant, `frontend/src/test/support/handlers/monthReview.ts`
- Modifier : `frontend/src/types/monthReview.ts` (`ReviewAccount` gagne `group`, `statement_date` et `statement_balance`)
- Modifier : `frontend/src/i18n/locales/{fr,en,es}/month.json` (espace `accountsStep`)
- Test : `frontend/src/test/components/month-review/ReviewSteps.test.tsx` (bloc `describe("AccountsStep")` réécrit)

**Interfaces :**
- Consomme : `postAccountsReconcile(id, { date: statement_date, bank_balance })` → `ReconcileResult` (tâche 3), et `postMonthReviewAccountsConfirmUnchanged({ year, month })` → la revue.
- Produit : `AccountsStep({ step, year, month, onChanged, onReview })`. `onReview(data)` remplace la revue dans la page après « Tout valider », sans rechargement supplémentaire.

Comportement :
- **Bloc « À rapprocher au {date} »** (groupe `reconcile`). Chaque ligne montre le nom du compte, « Numera : {statement_balance} » et un champ « Solde du relevé » (`inputMode="decimal"`, virgule acceptée et convertie en point). Le bouton « Vérifier », ou la touche Entrée, appelle `reconcile`.
  - Si les soldes collent : toast « Solde validé », `onChanged()`, et le focus passe au champ suivant.
  - Sinon : afficher « Écart de {gap} » (`formatCurrency`), puis `<ReconcileHints>` et un lien « Ouvrir le compte » vers `/accounts/{id}`.
  - Un lien secondaire « Valider sans saisir » appelle `postAccountsVerify`.
  - Un compte déjà vérifié affiche « ✅ Validé » à la place du champ.
- **Bloc « Rien n'a bougé depuis la dernière vérification ({count}) »** (groupe `unchanged`, masqué s'il est vide). Les noms des comptes sont séparés par « · ». Le bouton « Tout valider » n'apparaît que s'il reste un compte non vérifié du groupe.
- **Bloc « Placements (valeur actuelle) »** (groupe `market`, masqué s'il est vide) : même ligne qu'aujourd'hui (valeur et bouton « Valider le solde »).
- Les montants passent par `formatCurrency`. Mise en page mobile : une ligne par carte, champs en 16 px, cibles d'au moins 40 px.

- [ ] **Étape 1 : écrire les tests qui échouent**, dans `ReviewSteps.test.tsx`, avec MSW et `recordRequests` pour les corps envoyés :
  - `"rapproche un compte au solde du relevé et valide s'il colle"` : taper « 1 248,30 » puis Entrée. Vérifier la requête `POST /accounts/1/reconcile` avec le corps `{ date: "2025-10-31", bank_balance: 1248.3 }`, le toast « Solde validé » et un appel à `onChanged`.
  - `"affiche l'écart et la cause probable"` : la réponse a `matches: false, gap: -20` et une cause `duplicate`. Vérifier que « Écart de -20,00 € » et le message de la cause sont affichés.
  - `"valide tous les comptes qui n'ont pas bougé"` : clic sur « Tout valider ». Vérifier la requête `POST /month-review/accounts/confirm-unchanged` avec le corps `{ year: 2025, month: 10 }`, puis un appel à `onReview` avec la réponse.
  - `"garde les placements à part avec leur valeur actuelle"` : vérifier le titre « Placements (valeur actuelle) », l'absence de champ « Solde du relevé » dans ce bloc, et le bouton « Valider le solde ».
- [ ] **Étape 2 :** `cd frontend && npx vitest run src/test/components/month-review` doit échouer.
- [ ] **Étape 3 : implémenter** les wrappers API, le handler MSW, les types, le composant, le passage des props dans `MonthReview.tsx` et les traductions dans les trois langues.
- [ ] **Étape 4 :** `cd frontend && npm test && npm run build && npm run lint && npm run knip` doivent passer, y compris `catalogs.test.ts` et `apiCases`.
- [ ] **Étape 5 : vérification dans le navigateur.** Démarrer le dev server (`make backend-seed-demo`, puis le backend et le frontend), ouvrir `/month/revue`, faire un rapprochement juste, puis un faux, puis « Tout valider ». Contrôler aussi en largeur 375 px, en thème sombre et en mode confidentialité.
- [ ] **Étape 6 : commit** `feat(revue): rapprocher chaque compte au solde du relevé dans la revue de mois`

### Tâche 5 : finalisation

- [ ] `make validate` doit être vert.
- [ ] Mettre à jour `frontend/src/CLAUDE.md` si besoin (ligne sur la revue) et le skill `numera-expert` (section revue de mois : rapprochement à la date du relevé, groupes).
- [ ] Ouvrir la PR `feat(revue): rapprochement des comptes dans la revue de mois` au template, puis suivre le skill `numera-finishing`.
