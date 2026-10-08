# Virements internes fiables — design

## Problème

Le revenu arrive sur le compte principal, puis est réparti vers les autres comptes (Livret A, PEA, assurance-vie…). Sans lien entre la sortie et l'entrée, l'argent est compté deux fois (revenus gonflés, dépenses gonflées, taux d'épargne faussé). Le mécanisme actuel (`is_transfer`, `linked_transaction_id`, onglet Paramètres › Virements) existe mais n'est pas fiable :

- appariement au seul montant + date (±1 %, ±3 j), sans notion de compte de destination : deux virements de même montant vers deux comptes se confondent, une même entrée peut être proposée pour plusieurs sorties ;
- fenêtre de 6 mois, aucun rattrapage de l'historique ;
- aucune action « virement » depuis une transaction ; aucune automatisation (import, récurrences) ;
- bugs UI : le nom du compte de destination d'un virement lié est calculé avec l'id de la transaction liée ; liste limitée à 50 lignes ; « Ignorer » ne marque que la sortie.

## Besoin (validé)

- Virements **réguliers** (mensuels, montants fixes) **et asynchrones** (montants et dates variables).
- Liaison **automatique** quand le candidat est unique et exact, avec journal et possibilité de délier.
- **Rétroactif** et pris en compte dans les **récurrences**.
- Les couples restent **1 pour 1** (une sortie ↔ une entrée) : le modèle de lien actuel est conservé, les KPI (`api/analytics/`) excluent déjà `is_transfer` et ne changent pas.

## Conception

### 1. Données

- Table `transfer_rules` : `id`, `source_account_id`, `dest_account_id` (FK, `ondelete=CASCADE`), `pattern` (nullable, insensible à la casse, sur `merchant`/`note` de la sortie), `amount` (nullable), `amount_tolerance_pct` (défaut 1.0), `day_tolerance` (défaut 5), `is_active`, `created_at`. Destination de type `investissement` : la règle cible les `investment_transactions` de type `versement` (lien existant `linked_investment_transaction_id`).
- Colonnes sur `transactions` et `investment_transactions` : `link_origin` (`manual` | `rule` | `recurring`, nullable) et `transfer_rule_id` (FK `ondelete=SET NULL`, nullable).
- Colonne `recurring_transactions.transfer_to_account_id` (FK `accounts`, `ondelete=SET NULL`, nullable).
- Migration Alembic unique. Les liens existants gardent `link_origin = 'manual'`.

### 2. Moteur (`core/transfers.py`)

- `link_pair(db, tx, other, kind, origin, rule_id=None)` : logique de liaison extraite de `api/transactions.py::link_transactions` (détache d'abord les anciens partenaires), réutilisée par l'endpoint manuel, le moteur et la génération de récurrences.
- `match_transfer_rules(db, rule_ids=None, dry_run=False) -> list[Pair]` :
  1. sorties non liées, non ignorées du compte source, filtrées par `pattern` et `amount` ;
  2. candidats : entrées (ou `versement`) non liés du compte destination, montant dans la tolérance (comparaison en EUR via `get_exchange_rates`, comme `potential-transfers`), date dans `day_tolerance` ;
  3. appariement 1 pour 1 global, trié par (écart de date, écart de montant) : un candidat n'est jamais utilisé deux fois ;
  4. un couple est lié seulement s'il est sans ambiguïté (le candidat est le plus proche pour la sortie et la sortie est la plus proche pour le candidat) ; sinon il reste en suggestion.
  `dry_run` renvoie les couples sans écrire (aperçu du rattrapage).
- Déclencheurs : après `POST /import/commit`, après `generate_recurring_transactions` et `check_and_generate_pending_salaries`, après création / modification d'une transaction, et `POST /transfer-rules/apply` (rattrapage de l'historique, sans limite de 6 mois, `?dry_run=true` pour l'aperçu).
- **Garde-fou** : `unlink` d'un lien `rule` ou `recurring` marque les deux lignes `is_transfer_ignored = True` pour que la règle ne les relie pas à nouveau. Corriger au passage `ignore` pour marquer les deux côtés.
- Un lien ne modifie aucun montant : pas de recalcul de `running_balance` par la liaison seule (la création d'une contrepartie ou d'une jambe de récurrence le déclenche).

### 3. Récurrences

- Récurrences existantes (deux récurrences, une par compte) : liées par les règles, sans changement pour l'utilisateur.
- Nouvelle option « virement vers un compte » (`transfer_to_account_id`, forcément `type = Sortie`) : à chaque échéance, `core/recurring.py` crée la sortie (compte source) **et** l'entrée (compte destination, `Entree` ou `versement`), liées (`link_origin = 'recurring'`), conversion de devise via `convert_amount`, recalcul des soldes des deux comptes. Idempotence : la garde actuelle sur `last_generated_date`.
- Pas de migration automatique « deux récurrences → une ».

### 4. API

- `GET/POST/PATCH/DELETE /transfer-rules`, `POST /transfer-rules/apply[?dry_run=true]` (nouveau router, à ajouter à `protected_routers`).
- `GET /transactions/{id}/transfer-candidates?days=15&account_id=` : candidats classés pour la liaison manuelle, tous comptes, sens inverse, hors 6 mois.
- `POST /transactions/{id}/transfer-counterpart` `{account_id, date?, amount?}` : crée la contrepartie et la lie.
- `GET /transactions?is_transfer=true` sans limite implicite de 50 ; la réponse expose `link_origin` et le **compte** du partenaire (`linked_account_id`) pour corriger le bug d'affichage.
- `potential-transfers` conservé (suggestions), réécrit avec l'appariement global et sans la limite de 6 mois (paramètre `months`).

### 5. Interface

- `TransactionList` / recherche : action « Virement interne… » → panneau de candidats (filtre compte, fenêtre ±15 j), « Créer la contrepartie », « Ce n'est pas un virement ».
- Paramètres › Virements refondu en trois sections : Règles (CRUD, activer, « Rattraper le passé » avec aperçu), Suggestions (cas ambigus, incluant les entrées sans sortie), Liés (tous, avec comptes exacts et origine, « Délier »).
- Page Récurrences : champ « Virement vers le compte » dans le formulaire.
- Centre d'Actions : `unmatched-transfers` pointe vers l'onglet Virements.

### 6. Hors périmètre

- Liens 1 pour N (une sortie couvrant plusieurs entrées).
- Fusion automatique de deux récurrences.
- Détection de virements par apprentissage.

## Tests (`backend/tests/test_transfers.py`)

- Deux sorties de même montant vers deux comptes : chaque entrée est appariée au bon compte.
- Une entrée n'est jamais utilisée pour deux sorties ; cas ambigu laissé en suggestion.
- Délier un lien `rule` puis relancer : pas de reliaison.
- Rattrapage de l'historique (au-delà de 6 mois), aperçu `dry_run` sans écriture.
- Destination `investissement` : lien avec un `versement`.
- Récurrence « virement » : deux jambes liées, soldes recalculés, idempotent.
- Création de la contrepartie : lien, solde recalculé.
- Les KPI « dépenses réelles » et revenus excluent les couples liés par règle.
- Import CSV : les règles s'appliquent après le commit.

Documentation : `ARCHITECTURE.md` (modèle, routes), skill `numera-expert` (section Virements internes), `mcp-server/server_api.py` (règles de virement, liaison).
