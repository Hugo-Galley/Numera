# Architecture en couches — conception

Date : 2026-10-28 · Statut : validé (discussion du 28/10)

## Problème

- La logique métier et l'accès aux données sont dans les routers : 34 fichiers de `api/` font des `db.query`/`commit`.
- Les dépendances sont inversées : `core/` importe `api/` (`core/salary.py`, `core/recurring.py`, `core/demo.py` → `api.transactions.recalculate_running_balances` ; `core/notifications.py` appelle des **fonctions de route** ; `core/month_review.py`, `core/provisions.py` → `api.analytics.utils`), et des routers s'importent entre eux (`api/month_review.py` → `api/accounts.py` + `api/analytics/budget.py`, `api/tax.py` → `api/analytics/*`, `api/auth.py` ↔ `api/totp.py`/`api/passkeys.py`).
- `core/` mélange le transverse (config, sécurité), le métier (salaire, virements) et les appels externes (marché, notifications).
- Fichiers et fonctions géants : `api/analytics/investments.py` 1 372 lignes, `budget_analytics` ≈ 520 lignes, `get_action_center` ≈ 460, `compute_portfolio` ≈ 400 ; côté frontend `pages/AccountDetail.tsx` 2 773 lignes (83 `useState`), `RecurringTransactions.tsx` 1 548, `WealthSimulator.tsx` 1 169.

## Décision

Architecture **en couches pragmatique**, pas de Clean Architecture stricte : les modèles SQLAlchemy restent les objets métier, pas d'interfaces/ports abstraits, pas de `BaseRepository[T]` générique.

### Couches backend (`backend/app/`)

Le dossier des routers s'appelait `api/` jusqu'au 28/10/2026 (renommé en `controllers/`, phase 2 tâche 1).


| Couche | Rôle | Peut importer | Ne doit pas importer |
|---|---|---|---|
| `controllers/` | Controllers : HTTP, `Depends`, `Query`, schéma → réponse. Pas de `db.query`, pas de `commit`. | services, schemas, `controllers.deps`, core | un autre module `controllers.*` (sauf `controllers.deps` et les sous-routers de son propre package) |
| `services/` | Cas d'usage : orchestration, **transaction (commit)**, appels repositories + domain + integrations. Lève des erreurs métier (`app.core.errors`). | repositories, domain, integrations, models, schemas, core | `app.controllers`, `fastapi` |
| `repositories/` | Accès aux données : requêtes SQLAlchemy, agrégats SQL. Pas de règle métier, pas de `commit` (`flush` autorisé). | models, db, core | `app.controllers`, `app.services`, `app.integrations`, `fastapi` |
| `domain/` | Calculs purs (solde, salaire net, XIRR/TWR, KPI, revenu…). Aucune Session. | models (comme types), schemas, core | `app.controllers`, `app.services`, `app.repositories`, `app.integrations`, `app.db`, `sqlalchemy.orm`, `fastapi` |
| `integrations/` | Appels externes : Frankfurter, données de marché, ntfy/Telegram, logos, backup. | models, schemas, core, db | `app.controllers`, `app.services`, `app.repositories` |
| `core/` | Transverse : config, security, logging, errors, time, rate limit, mcp_tokens. **Pendant la migration**, couche héritée qui contient encore du métier : seule interdiction `app.controllers`. Règle durcie en fin de migration (n'importe plus que core). | — | `app.controllers` (puis tout sauf core) |
| `models/`, `schemas/`, `db/` | Inchangés. | — | `app.controllers`, `app.services`, `app.repositories`, `app.integrations` |

Analytics : côté lecture dédié, `repositories/analytics/` (requêtes d'agrégat) + `services/analytics/` (assemblage) + `domain/` (formules). Pas de repository par entité pour les KPI.

Erreurs : un service lève `NotFoundError` / `BusinessRuleError` / `ConflictError` (`app.core.errors`) ; un handler dans `main.py` les traduit en 404/422/409 avec **le même corps JSON qu'aujourd'hui** (`detail` chaîne, ou `{"code","detail","context"}` si un `code` est fourni).

### Couches frontend (`frontend/src/`)

- `pages/<Page>/index.tsx` : composition et mise en page seulement.
- `pages/<Page>/` ou `components/<domaine>/` : un composant par section/dialogue.
- `hooks/` ou `pages/<Page>/use*.ts` : chargement des données et état.
- `lib/api/<domaine>.ts` : fonctions d'accès typées (équivalent data-access), au-dessus de `lib/api.ts`.

### Limites de taille

| | Cible | Plafond (bloquant) |
|---|---|---|
| Fichier Python (`backend/app`) | ~200 lignes | 400 |
| Fonction Python | ~40 lignes | 80 |
| Fichier `.ts`/`.tsx` (`frontend/src`, hors `components/ui`) | ~200 lignes | 350 |

Au-delà : package (backend) ou dossier (frontend), un module par responsabilité. Le Centre d'Actions devient un registre de règles (un module par règle).

### Garde-fous automatiques (cliquet)

- `scripts/check_code_size.py` + `scripts/code_size_baseline.json` : un fichier/une fonction au-dessus du plafond échoue, sauf s'il est dans la baseline **et** n'a pas grossi ; une entrée de baseline repassée sous le plafond doit être retirée. Lancé par `make validate` et par un test pytest.
- `backend/tests/test_architecture.py` + `backend/tests/architecture_baseline.txt` : règles d'import du tableau ci-dessus (imports de module et imports locaux dans les fonctions). Une violation hors baseline échoue ; une entrée de baseline qui ne se produit plus échoue aussi.
- Les deux baselines ne peuvent que diminuer. Fin de migration = baselines vides.

## Migration

Progressive, domaine par domaine, `main` toujours vert. Les 366 tests passent par l'API HTTP : ils restent le filet de sécurité. Phases : 0 garde-fous · 1 fondations (cycles cassés, domaine modèle `accounts`) · 2 domaines d'écriture · 3 analytics · 4 portefeuille · 5 frontend · 6 nettoyage et durcissement. Chaque phase ≥ 2 a son propre plan détaillé, écrit à son ouverture.

## Hors périmètre

Changement de comportement, de route, de schéma de réponse ou de base ; serveur MCP (il consomme l'API HTTP, inchangée) ; lint/tests frontend.
