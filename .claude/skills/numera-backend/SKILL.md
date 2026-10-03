---
name: numera-backend
description: Procédures pour modifier le backend Numera (FastAPI, SQLAlchemy 2, Alembic, Pydantic v2) : ajouter un endpoint ou un router, un modèle + migration, un KPI analytics, une tâche de fond. À charger dès qu'on édite backend/app/.
---

# Numera backend — procédures

Conventions et pièges : `backend/CLAUDE.md` (à lire d'abord). Règles métier : skill `numera-expert`.

## Ajouter un endpoint dans un router existant

1. Schémas `Create` / `Update` / `Read` dans `app/schemas/<domaine>.py` (`ConfigDict(from_attributes=True)` sur `Read`).
2. Endpoint dans `app/api/<domaine>.py` avec `response_model`, `db: Session = Depends(get_db)`. Pas de `Depends(get_current_user)` à ajouter : le router est déjà protégé dans `main.py`.
3. Mutation de transactions → `db.commit()` puis `recalculate_running_balances(db, account_id)` (importé depuis `app.api.transactions`), pour chaque compte touché.
4. Ordre des routes FastAPI : déclarer les chemins fixes (`/bulk`, `/merchants`, `/potential-transfers`, `/auto-normalize`) **avant** `/{id}`.
5. Test dans `backend/tests/test_<domaine>.py`.
6. Mettre à jour `ARCHITECTURE.md` (routes) et, si le serveur MCP expose le domaine, `mcp-server/server_api.py`.

## Ajouter un nouveau router

Créer `app/api/<nom>.py` (`APIRouter(prefix="/<nom>", tags=[...])`), l'importer dans `app/main.py` **et** l'ajouter à `protected_routers`. Sans ça la route n'existe pas / ou n'est pas protégée.

## Modifier le schéma de base

1. Modèle dans `app/models/` (nouveau fichier → l'importer dans `app/models/__init__.py` sinon Alembic et les tests ne le voient pas).
2. `cd backend && alembic revision --autogenerate -m "description"` ; relire le fichier généré dans `alembic/versions/` (SQLite : `batch_alter_table` pour altérer/supprimer des colonnes).
3. Les migrations tournent au démarrage (`core/migrations.py`) ; tester en local avec `alembic upgrade head` sur une copie de la base.
4. Si la table est exposée au MCP SQLite (`mcp-server/server_sqlite.py`), vérifier la compatibilité.

## Ajouter un KPI / graphe

1. Calcul dans le module adapté de `app/api/analytics/` (`metrics`, `budget`, `investments`, `reports`, `subscriptions`, `insights`, `audit`) ; réutiliser `analytics/utils.py`. Ne jamais déplacer le calcul côté frontend.
2. Schéma de réponse dans `app/schemas/insight.py` (ou `investment.py`) et `response_model`.
3. Respecter : exclusion de `Solde Initial` des revenus/dépenses, exclusion des transferts internes pour les « dépenses réelles », filtres `account_id` / `month` / `year` cohérents avec les endpoints voisins.
4. Test dans `tests/` (cf. `test_import_and_analytics.py`, `test_money_flow.py`, `test_sankey.py`), puis consommer l'endpoint dans le frontend.

## Ajouter un type d'action au Centre d'Actions

Voir `docs/ACTION_CENTER.md` ; `ActionItem.id` doit être déterministe.

## Tâche de fond

`recurring_transactions_task` dans `app/main.py` (toutes les heures). Y ajouter du travail périodique plutôt que de créer une nouvelle boucle ; ouvrir/fermer sa propre `SessionLocal()`.

## À ne pas faire

- `db.execute(text(...))` sauf nécessité de performance.
- Logique métier dans les modèles.
- Logger/retourner `SECRET_KEY`, hash de mot de passe, JWT.
- Appels réseau sortants autres que Frankfurter / Yahoo Finance ; toute nouvelle dépendance externe doit être discutée (principe local-first).
- Modifier la base `*.db` directement ou la committer.
