# Revue de fin de mois guidée — design

Date : 2026-10-13 · Statut : validé en conversation, en attente de relecture du spec.
Origine : ROADMAP.md, « Idées retenues (octobre 2026) », point 4.

## 1. Objectif

Une fois par mois, un parcours guidé en cinq étapes fait passer en revue le mois écoulé : catégoriser ce qui traîne, valider les soldes, comparer au budget, noter un fait marquant, puis clôturer. L'application sait ensuite quels mois ont été revus.

Principes validés :

- **Clôturer = marquer, pas verrouiller.** Aucune écriture n'est bloquée sur un mois clôturé (imports CSV idempotents, remboursements tardifs). L'application signale seulement « modifié depuis la clôture ».
- **Aucune transaction n'est créée** pendant la revue.
- **Calculs côté backend uniquement** (règle métier n°2 du projet).
- Tous les comptes sont couverts par le parcours, pas un seul.

## 2. Données

### 2.1 Table `month_closures` (nouvelle)

| Colonne | Type | Remarque |
|---|---|---|
| `id` | int, PK | |
| `year`, `month` | int | contrainte d'unicité sur `(year, month)` |
| `closed_at` | datetime | `utcnow_naive()`, comme `last_verified_at` |
| `highlight` | string, nullable | fait marquant saisi à l'étape 4 |
| `tx_count` | int | photo à la clôture |
| `income` | float | photo à la clôture (revenus du mois) |
| `expenses` | float | photo à la clôture (dépenses réelles nettes) |
| `unresolved_count` | int | points restants à la clôture (étapes 1 et 2) |

Rouvrir un mois supprime sa ligne. Re-clôturer remplace la photo.

### 2.2 Colonne `transactions.is_exceptional` (nouvelle)

Booléen, `default=False`, `server_default="0"`, non nul. Exposée dans les schémas de lecture et de mise à jour des transactions.

Une seule migration Alembic crée la table et la colonne (`backend/alembic/versions/`).

## 3. Backend

Nouveau router `app/api/month_review.py`, à ajouter à la liste `protected_routers` de `main.py` (JWT obligatoire).

| Route | Rôle |
|---|---|
| `GET /month-review?year=&month=` | État du mois : étapes 1 à 3 calculées, statut de clôture, indicateur `modified_since_close`. |
| `POST /month-review/close` | Corps : `year`, `month`, `highlight` optionnel. Prend la photo, crée ou remplace la ligne. |
| `DELETE /month-review?year=&month=` | Rouvre le mois (supprime la ligne). |
| `GET /month-review/closures` | Liste des mois clôturés, plus récents d'abord. |

### 3.1 Étape 1 — Catégoriser

`/analytics/actions` est **global** (tous mois confondus) ; la revue est par mois. L'étape fait donc ses propres requêtes **bornées au mois**, avec les mêmes filtres que l'audit : transactions `Sortie`, `is_transfer` faux, sans catégorie, doublons non ignorés (`is_duplicate_ignored`). Le Centre d'Actions n'est pas modifié.

### 3.2 Étape 2 — Soldes

Pour chaque compte : solde affiché, `last_verified_at`, et indicateur « vérifié depuis la fin du mois ou non ». La validation réutilise la route existante qui met à jour `last_verified_at` (`api/accounts.py`). Aucune nouvelle logique de solde.

### 3.3 Étape 3 — Comparaison au budget

Réutilise `budget_analytics` et la logique de `/analytics/monthly-report`. S'y ajoutent des champs `*_excl_exceptional` :

- dépenses réelles, épargne, taux d'épargne, burn rate, calculés avec `NET_AMOUNT` (`analytics/utils.py`) filtré sur `is_exceptional = False`.

Le total officiel ne change pas : une dépense exceptionnelle reste dans les dépenses réelles et dans le solde. Les alertes budget par catégorie et la projection de fin de mois **ne sont pas modifiées**.

### 3.4 « Modifié depuis la clôture »

À la lecture, le backend recalcule `tx_count`, `income` et `expenses` du mois et les compare à la photo. Un écart passe `modified_since_close` à vrai. Un simple changement de catégorie, qui ne bouge pas les totaux, ne déclenche pas l'indicateur (choix assumé : pas de `updated_at` sur `Transaction`).

### 3.5 Clôture

La clôture n'est jamais bloquée par des points non résolus. `unresolved_count` est enregistré et affiché dans le récap (« clôturé avec 3 transactions non catégorisées »).

## 4. Frontend

- **Page `/month-review`** (route protégée dans `App.tsx`), paramètres `?year=&month=`. Bandeau de cinq étapes, une étape visible à la fois, état « OK » ou « à traiter » par pastille, toutes passables.
  1. Catégoriser · 2. Soldes · 3. Budget · 4. Fait marquant · 5. Clôturer.
- **Étape 3** : le mois est montré avec et sans dépenses exceptionnelles, et chaque dépassement permet de « marquer exceptionnelle » les transactions concernées.
- **Éditeur de transaction** : case « Exceptionnelle ».
- **Pop-up Dashboard** :
  - Déclencheur : à l'ouverture du Dashboard, si le **mois précédent** n'est pas clôturé, à partir du 1er du mois en cours.
  - Boutons : « Faire la revue » (mène à `/month-review`), « Plus tard » (masquée pour la journée), « Pas ce mois-ci » (masquée jusqu'au mois suivant, sans clôturer).
  - « Plus tard » et « Pas ce mois-ci » sont mémorisés dans `localStorage` (lecture et écriture dans un try/catch, la page fonctionne sans). L'état « clôturé » vit en base.
  - Un seul mois concerné, jamais une pile de mois en retard ; les mois plus anciens restent accessibles à la main.
- Les montants respectent le **mode confidentialité**.

## 5. Serveur MCP (lecture seule)

Deux outils ajoutés à `mcp-server/server_api.py` : `get_month_review` et `list_month_closures`, sur des routes `GET`. La clôture et la réouverture restent côté UI, conformément à la règle « pas d'outil d'écriture ». Si `server_sqlite.py` expose les mêmes domaines, l'équivalent y est ajouté.

## 6. Tests et documentation

Tests backend (`backend/tests/test_month_review.py`) :

- la clôture crée la photo et la ligne ; re-clôturer remplace ;
- la réouverture supprime la ligne ;
- `modified_since_close` passe à vrai après l'ajout d'une transaction dans le mois ;
- l'étape 1 est bornée au mois (une dépense sans catégorie d'un autre mois est ignorée) ;
- les chiffres « hors exceptionnel » sont justes, et les totaux officiels et `running_balance` sont inchangés ;
- l'endpoint répond `200` sur un mois vide.

Frontend : `npm run build` (seule vérification disponible).

Documentation mise à jour dans le même commit que le code : `ARCHITECTURE.md` (modèle et routes), `mcp-server/README.md`, skill `numera-expert` si une règle métier est ajoutée, et ROADMAP.md (point 4 marqué réalisé).

## 7. Hors périmètre

- Verrouillage d'un mois clôturé.
- Lien d'une dépense vers une « grosse dépense annuelle » provisionnée ou vers un objectif d'épargne (le drapeau `is_exceptional` pourra servir de base).
- Prise en compte des exceptionnelles dans les alertes budget et la projection de fin de mois.
- Détection d'un changement qui laisse les totaux identiques (nécessiterait un `updated_at`).
- Remboursements en attente et dividendes manquants traités à part : ils restent dans le Centre d'Actions.
