---
name: numera-backend
description: Procédures pour modifier le backend Numera (FastAPI, SQLAlchemy 2, Alembic, Pydantic v2) : ajouter un endpoint ou un router, un modèle + migration, un KPI analytics, une tâche de fond. À charger dès qu'on édite backend/app/.
---

# Numera backend — procédures

Conventions et pièges : `backend/CLAUDE.md` (à lire d'abord). Règles métier : skill `numera-expert`. Toute procédure ci-dessous commence par un test rouge (`numera-tdd`) ; où placer le code et comment déplacer : `numera-clean-architecture`.

## Ajouter un endpoint dans un router existant

1. Schémas `Create` / `Update` / `Read` dans `app/schemas/<domaine>.py` (`ConfigDict(from_attributes=True)` sur `Read`).
2. Requêtes dans `app/repositories/<domaine>/<sujet>.py` (sans `commit`), logique dans `app/services/<domaine>/<sujet>.py` (commit, erreurs `NotFoundError`/`BusinessRuleError`/`ConflictError` de `app.core.errors`, jamais `HTTPException`), calcul pur dans `app/domain/`. Modèle : `accounts` (`comptes/accounts.py` dans les trois couches). Domaines : `budget`, `comptes`, `investissement`, `analytics`, `audit` (services), `systeme` ; même arborescence dans les trois couches.
3. Endpoint dans `app/controllers/<domaine>/<sujet>.py` : `response_model`, `db: Session = Depends(get_db)`, une ligne qui appelle le service. Pas de `Depends(get_current_user)` à ajouter : le router est déjà protégé dans `main.py`.
4. Mutation de transactions → `recalculate_running_balances(db, account_id)` (`app.services.budget.balances`) pour chaque compte touché, **puis `db.commit()`** : le recalcul ne fait qu'un `flush`.
5. Ordre des routes FastAPI : déclarer les chemins fixes (`/bulk`, `/merchants`, `/potential-transfers`, `/auto-normalize`) **avant** `/{id}`.
6. Tests : service (`db_session`, sans HTTP) et route (`client`) dans `backend/tests/<domaine>/test_<sujet>.py`. `tests/garde_fous/test_architecture.py` (un controller n'importe pas un controller d'un autre domaine) et `scripts/check_code_size.py` doivent rester verts.
7. Mettre à jour `ARCHITECTURE.md` (routes) et, si le serveur MCP expose le domaine, `mcp-server/server_api.py`.

## Ajouter un nouveau router

Créer `app/controllers/<domaine>/<nom>.py` (`APIRouter(prefix="/<nom>", tags=[...])`, avec ses `services/<domaine>/<nom>.py` et `repositories/<domaine>/<nom>.py`), l'importer dans `app/main.py` **et** l'ajouter à `protected_routers`. Sans ça la route n'existe pas / ou n'est pas protégée.

## Modifier le schéma de base

1. Modèle dans `app/models/` (nouveau fichier → l'importer dans `app/models/__init__.py` sinon Alembic et les tests ne le voient pas).
2. `cd backend && alembic revision --autogenerate -m "description"` ; relire le fichier généré dans `alembic/versions/` (SQLite : `batch_alter_table` pour altérer/supprimer des colonnes).
3. Les migrations tournent au démarrage (`core/migrations.py`) ; tester en local avec `alembic upgrade head` sur une copie de la base.
4. Si la table est exposée au MCP SQLite (`mcp-server/server_sqlite.py`), vérifier la compatibilité.

## Ajouter un KPI / graphe

1. Calcul dans `app/services/analytics/` (nouveau KPI) (route dans `app/controllers/analytics/`, une ligne qui appelle le service) ; requêtes partagées : `app/repositories/analytics/common.py` (`NET_AMOUNT`, `income_criterion`, `category_lines`…), calculs purs : `app/domain/`. Appeler un autre KPI via son service (`compute_budget`…), jamais via une fonction de route. Ne jamais déplacer le calcul côté frontend.
2. Schéma de réponse dans `app/schemas/insight.py` (ou `investment.py`) et `response_model`.
3. Respecter : exclusion de `Solde Initial` des revenus/dépenses, exclusion des transferts internes pour les « dépenses réelles », filtres `account_id` / `month` / `year` cohérents avec les endpoints voisins.
4. Test dans `tests/` (cf. `test_import_and_analytics.py`, `test_money_flow.py`, `test_sankey.py`), puis consommer l'endpoint dans le frontend.

## Ajouter un type d'action au Centre d'Actions

Créer `services/audit/rules/<nom>.py` avec `detect(ctx)`, l'ajouter à `RULES` (`services/audit/__init__.py`) ; requêtes dans `repositories/analytics/audit.py`. Détails : `docs/ACTION_CENTER.md` ; `ActionItem.id` doit être déterministe.

## Tâche de fond

`recurring_transactions_task` dans `app/main.py` (toutes les heures). Y ajouter du travail périodique plutôt que de créer une nouvelle boucle ; ouvrir/fermer sa propre `SessionLocal()`.

## À ne pas faire

- `db.execute(text(...))` sauf nécessité de performance.
- Logique métier dans les modèles.
- Logger/retourner `SECRET_KEY`, hash de mot de passe, JWT.
- Appels réseau sortants autres que Frankfurter / Yahoo Finance / canaux de notification activés par l'utilisateur (ntfy, Telegram) ; toute nouvelle dépendance externe doit être discutée (principe local-first).
- Modifier la base `*.db` directement ou la committer.
