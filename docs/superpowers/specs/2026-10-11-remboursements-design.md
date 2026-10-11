# Remboursements et dépenses avancées — design

## Problème

Une dépense avancée pour d'autres (resto payé pour trois, consultation médicale, achat retourné) est comptée en entier dans les dépenses, et son remboursement est compté comme un revenu (catégorie « Remboursement (recu) »). Les dépenses et les revenus sont donc gonflés tous les deux, le taux d'épargne et le budget par catégorie sont faussés, et rien ne dit qui doit encore de l'argent.

## Besoin (validé)

- Cas couverts : avances entre amis/famille, santé (Sécu puis mutuelle), retours / remboursements marchands. Hors périmètre : notes de frais.
- Sur une `Sortie`, déclarer une ou plusieurs **créances** : un débiteur (texte libre) et un montant attendu.
- Lier ensuite les `Entree` de remboursement aux créances, avec un **montant affecté** : plusieurs entrées par créance (Sécu + mutuelle), plusieurs créances par entrée (un virement qui rembourse deux dépenses).
- KPI **nets sur le mois et la catégorie de la dépense** : la dépense compte pour son montant moins ce qui a été reçu ; la part affectée d'un remboursement n'est pas un revenu.
- Liste « ce qu'on me doit » : créances ouvertes, reste dû par débiteur.
- Une créance qui ne sera pas entièrement remboursée se clôt en **ajustant le montant attendu** au montant reçu (à 0 reçu : suppression de la créance). Pas de remboursement en espèces.

## Conception

### 1. Données

- Table `reimbursement_claims` : `id`, `transaction_id` (FK `transactions`, `ondelete=CASCADE`, index), `debtor` (str, obligatoire, ≤ 120), `expected_amount` (float > 0, devise du compte de la dépense), `note` (nullable), `created_at`. Reçu et reste dû sont calculés à la lecture, jamais stockés.
- Table `reimbursement_allocations` : `id`, `claim_id` (FK, `ondelete=CASCADE`, index), `entree_transaction_id` (FK `transactions`, `ondelete=CASCADE`, index), `amount` (float > 0), `created_at`. Contrainte d'unicité `(claim_id, entree_transaction_id)` : réaffecter la même entrée à la même créance met à jour le montant.
- Colonne `transactions.reimbursement_offset` (float, non nul, défaut 0) : pour une `Sortie`, somme des affectations de ses créances ; pour une `Entree`, somme de ses affectations ; 0 sinon.
- Migration Alembic unique (`batch_alter_table` pour la colonne).

### 2. Moteur (`core/reimbursements.py`)

Seule porte d'entrée pour créer / modifier / supprimer créances et affectations ; chaque mutation se termine par `sync_offsets(db, tx_ids)` qui recalcule `reimbursement_offset` des transactions touchées à partir des tables (pas d'incrément : recalcul intégral par transaction).

Règles vérifiées à l'écriture (`HTTPException` 400, message explicite) :

1. Une créance porte sur une `Sortie` ; une affectation part d'une `Entree` (n'importe quel compte, y compris celui de la dépense).
2. Dépense et remboursement ont la même `currency`.
3. Ni l'une ni l'autre n'est un virement interne (`is_transfer`). Inversement, lier comme virement (`core/transfers.py::link_pair`) une transaction qui porte des créances ou des affectations est refusé, et `find_pairs` / `candidates_for` l'excluent (`reimbursement_offset > 0` ou créance existante).
4. Somme des affectations d'une créance ≤ `expected_amount` ; somme des affectations d'une `Entree` ≤ son `amount` ; somme des `expected_amount` d'une `Sortie` ≤ son `amount`.
5. Baisser `expected_amount` sous le total déjà reçu est refusé.
6. Modifier une transaction liée (`amount`, `type`, `currency`, `account_id` si la devise change) est refusé si cela viole 1, 2 ou 4 — contrôle appelé depuis `PUT/PATCH /transactions/{id}` et le bulk update.
7. Suppression d'une transaction : la cascade SQLite supprime créances / affectations ; avant la suppression, on collecte les transactions de l'autre côté et on appelle `sync_offsets` après.

Montant affecté par défaut (`amount` absent) : `min(reste dû de la créance, part non affectée de l'entrée)` ; s'il vaut 0, refus.

**Candidates** d'une créance : `Entree` non virement, même devise, part non affectée > 0, datée de `dépense − 7 j` à `dépense + 180 j`. Tri : libellé (`merchant` ou `note`) contenant le débiteur (insensible à la casse) d'abord, puis part disponible égale au reste dû, puis écart de date. 30 résultats au plus. Aucune liaison automatique.

### 3. API (`api/reimbursements.py`, préfixe `/reimbursements`, ajouté à `protected_routers`)

| Route | Rôle |
|---|---|
| `GET /reimbursements/claims?status=open\|settled\|all&debtor=` | Créances avec dépense (id, date, libellé, compte, montant, devise), attendu, reçu, reste dû, affectations (id, entrée, montant). `open` par défaut = reste dû > 0. |
| `GET /reimbursements/summary` | `total_due`, et par débiteur : `debtor`, `claims`, `due`. |
| `POST /reimbursements/claims` | `{transaction_id, debtor, expected_amount, note?}` |
| `PATCH /reimbursements/claims/{id}` | `debtor`, `expected_amount`, `note` |
| `DELETE /reimbursements/claims/{id}` | Supprime la créance et ses affectations. |
| `GET /reimbursements/claims/{id}/candidates` | Entrées candidates (cf. moteur), avec `available`. |
| `POST /reimbursements/claims/{id}/allocations` | `{entree_id, amount?}` |
| `DELETE /reimbursements/allocations/{id}` | Retire une affectation. |
| `GET /reimbursements/entries/{entree_id}/claims` | Créances ouvertes pour affecter une `Entree` donnée (même devise, débiteur reconnu dans le libellé en premier) et affectations existantes de cette entrée. |

Schémas dans `schemas/reimbursement.py` (`Create` / `Update` / `Read`, `response_model` partout). Les sommes et comparaisons sont arrondies au centime (`round(x, 2)`) pour éviter les refus dus aux flottants.

`TransactionRead` expose `reimbursement_offset` et `has_claims` (booléen ; calculé par une relation `claims` en `lazy="selectin"`).

MCP (`mcp-server/server_api.py`) : `list_reimbursement_claims`, `create_reimbursement_claim`, `allocate_reimbursement`, `delete_reimbursement_claim`.

### 4. KPI (`api/analytics/`)

Une définition dans `analytics/utils.py` : `NET_AMOUNT = Transaction.amount - Transaction.reimbursement_offset` (requêtes SQL) et `net_amount(tx)` (boucles Python).

- **Net** : `/analytics/budget` (revenus, dépenses, taux d'épargne, ventilation par catégorie), `/budget-alerts`, `/expenses-by-category`, `/top-merchants`, `/tags`, `/kpi-history`, `/timeseries` (séries revenus/dépenses), `/monthly-report`, `/money-flow`, `/sankey`, `/insights`.
- **Brut** (flux de trésorerie réels) : soldes et `running_balance`, `/account-flow-summary`, `/calendar`, `/cashflow-projection`, `/subscriptions`, `/tax`.

Conséquence assumée : l'arrivée d'un remboursement fait baisser rétroactivement les dépenses du mois de la dépense.

### 5. Interface

- Page `pages/Reimbursements.tsx` (route `/reimbursements`, Sidebar, Omnibox) : total dû + cartes par débiteur (filtre), liste des créances ouvertes (date, dépense, débiteur, barre reçu/attendu, reste dû ; actions Lier un remboursement / Modifier / Supprimer), onglet « Soldées ». `amount-blur` sur tous les montants, `toast` après chaque mutation, `Skeleton`, état vide.
- `components/reimbursements/ReimbursementDialog.tsx`, ouvert depuis une ligne d'`AccountDetail` :
  - sur une `Sortie` : créances de la dépense (ajout débiteur + montant, « Répartir à parts égales sur N personnes »), affectations reçues ;
  - sur une `Entree` : créances ouvertes proposées (`/entries/{id}/claims`), montant à ventiler par créance.
- `components/reimbursements/ClaimCandidatesDialog.tsx` : candidates d'une créance (page Remboursements).
- Badge sur la ligne de transaction : « À rembourser », « Partiel » ou « Remboursé » ; montant net en petit sous le brut quand `reimbursement_offset > 0`.

### 6. Centre d'Actions

Issue `unallocated-reimbursements` dans `/analytics/audit` : `Entree` de catégorie « Remboursement (recu) » des 180 derniers jours avec `reimbursement_offset = 0`, remontée seulement s'il existe au moins une créance ouverte. Action : lien vers `/reimbursements`. Documenter dans `docs/ACTION_CENTER.md`.

### 7. Tests (`backend/tests/test_reimbursements.py`)

- Scénario de référence : Sortie resto 90 € le 28/09, créances Denis 30 € et Julie 30 €, Entree Denis 30 € le 03/10 affectée → `/analytics/budget` septembre : dépenses −30 € par rapport au brut, catégorie Restaurants à 60 € ; octobre : revenus sans les 30 €. Même vérification sur chaque endpoint « net » ; un endpoint « brut » inchangé.
- Sécu 21 € + mutuelle 9 € sur une créance de 30 € → soldée.
- Un virement de 50 € réparti sur deux créances (30 € + 20 €).
- Règles 1 à 6 refusées avec 400 ; montant par défaut ; réaffectation qui met à jour.
- Suppression de la dépense et de l'entrée → offsets de l'autre côté recalculés.
- Exclusion mutuelle avec les virements internes.
- Candidates : tri par débiteur dans le libellé.
- Issue d'audit présente / absente.

### 8. Documentation

`ARCHITECTURE.md` (tables, routes), skill `numera-expert` (section Remboursements), `docs/ACTION_CENTER.md`, `mcp-server/README.md` (nombre d'outils), `CLAUDE.md` racine (nombre d'outils MCP), `ROADMAP.md` (point 2 réalisé).

## Hors périmètre

Liaison automatique, rappels aux débiteurs, remboursements en espèces, devises différentes entre dépense et remboursement, notes de frais, remboursement d'opérations d'investissement.
