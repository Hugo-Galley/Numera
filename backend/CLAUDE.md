# Backend — conventions (FastAPI / SQLAlchemy 2 / Pydantic v2)

Complète le `CLAUDE.md` racine. Procédures pas-à-pas : skill `numera-backend`. Routes et schéma de données : `ARCHITECTURE.md`.

## Structure et cycle de vie

- `app/main.py` : `lifespan` → `run_migrations()` (Alembic ; un échec **bloque le démarrage**, pas de `stamp head` automatique) + `seed_all()` (catégories par défaut + profils ETF système), sauf si `APP_ENV=test`. Lance aussi `recurring_transactions_task` : boucle asynchrone (1er passage après 10 s, puis toutes les heures) qui appelle `generate_recurring_transactions`, `check_and_generate_pending_salaries` et `refresh_held_prices` (cours des titres détenus).
- Routers : tous dans `protected_routers` (`Depends(get_current_user)`) sauf `health` et `auth`. `api/analytics/` agrège 7 sous-routers sous le préfixe `/analytics` (`__init__.py`), plus `analytics/diversity.py` enregistré séparément.
- `api/deps.py` : `get_db` (session par requête) et `get_current_user` (décode le JWT, compare `sub` à `admin_username` lu dans `system_settings` avec repli sur `settings.ADMIN_USERNAME`).
- Sessions de **test** : `conftest.py` surcharge `get_db` (deux chemins : `app.db.session` et `app.api.deps`) et `get_current_user`.

## Règles de code

- Typer arguments et retours. Logger : `from app.core.logging import get_logger; logger = get_logger(__name__)` (jamais de `print`, jamais de JWT/hash/secret dans les logs).
- Erreurs : `app.core.errors.api_error(status, code, detail, context)` pour les erreurs métier structurées ; sinon `HTTPException` (400 règle métier, 401/403 auth, 404 introuvable).
- Modèles : `Mapped` / `mapped_column`, index sur `account_id`, `date`, `merchant`, FK. Pas de logique métier dans les modèles → `app/core/` ou `app/api/`.
- Schémas : `Create` / `Update` / `Read` séparés, `ConfigDict(from_attributes=True)` sur les `Read`, `response_model` sur chaque endpoint (pas de `dict` brut).
- Les endpoints sont majoritairement **synchrones** (`def`) ; `async def` seulement quand on appelle du code async (`convert_amount`, `get_exchange_rates`, `market_data`, `etf_analyzer`, génération récurrente).
- N+1 : relations en `lazy="selectin"` sur les modèles ; sinon `joinedload`/`selectinload` pour les listes.
- Dates : `app.core.time.utcnow_naive` (datetimes naïfs UTC en base).
- Schéma modifié → `cd backend && alembic revision --autogenerate -m "..."`, relire la migration, la committer. Les migrations s'appliquent seules au démarrage.

## Finance

- Montants **toujours positifs** en base ; `type` donne le sens. `apply_transaction_to_balance` : `Entree`/`Interets` ajoutent, `Sortie` retranche, `Solde Initial` **remplace** le solde. (`finance.py`)
- Toute mutation de transaction (create / update / delete / bulk / liaison de virement / import) → `recalculate_running_balances(db, account_id)`, définie dans **`app/api/transactions.py`** (pas dans `core/`). Recalcul intégral par ordre chronologique.
- Devises : `await convert_amount(...)` / `await get_exchange_rates()` (`core/currency.py`). Stocker `amount` (devise du compte) et garder `original_amount` + `currency`. Conversion datée par taux croisé via l'EUR pour toute paire ; sans taux exploitable `CurrencyConversionError` (→ HTTP 422 via le handler de `main.py`), **jamais** de repli 1:1.
- Positions : `portfolio_holdings` est **dérivé**. Après toute mutation d'opération d'investissement ou de l'inventaire Point Zéro (`holding_baseline_items`), appeler `await rebuild_holdings(db, account_id)` (`core/holdings.py`) : inventaire + opérations sur titres postérieures à `accounts.holdings_baseline_date`, PRU en moyenne pondérée frais inclus (devise de la position), vente sans effet sur le PRU, `cost_basis_eur` aux taux historiques. Ne jamais écrire `quantity`/`buy_price_avg` directement.
- Valorisation : `core/portfolio.py::compute_portfolio` (valeur = positions × cours + espèces, plus-values latente/réalisée, XIRR/TWR, courbe, rapprochement) ; un compte `investissement` avec positions n'est plus valorisé par snapshot (`uses_positions`). `core/holdings.py::replay_account` rejoue aussi les ventes (plus-value réalisée) et les variations de quantité.
- Cours : `get_market_quotes(symbols, db=db)` enregistre chaque cotation dans `security_prices` et renvoie le dernier cours stocké (`stale=True`) si Yahoo échoue ; `get_price_on(db, ticker, date)` pour un cours historique.
- Solde Initial : un seul par compte et chronologiquement premier ; contrôle centralisé dans `validate_solde_initial` (`api/transactions.py`) pour create/update, et dans l'import.
- SQLite : `PRAGMA foreign_keys=ON` est posé à chaque connexion (`db/session.py`, aussi dans `conftest.py`) : les `ondelete` sont effectifs. Une FK sans `ondelete` (ex. `salary_configs`) oblige à mettre la référence à `NULL` avant de supprimer la cible.
- Virements internes : `is_transfer`, `linked_transaction_id`, `is_transfer_ignored` ; un virement vers un compte `investissement` peut être lié à une `investment_transaction` (`linked_investment_transaction_id`). Les KPI « dépenses réelles » excluent ces transferts.
- Marchés : `core/market_data.py` interroge **Yahoo Finance** (`query2.finance.yahoo.com`, via `httpx`) pour la recherche de titres et les cotations ; `core/etf_analyzer.py` en déduit des profils ETF (pays/secteurs/top holdings). Ce sont, avec Frankfurter, les seuls appels réseau sortants.
- Salaire : `core/salary.py::generate_salary_transactions` crée une seule transaction `Entree` « Salaire » (`net_salary − nb_jours_TT × ticket_employee_share`, aucune transaction TR) à partir de `SalaryConfig` et des `TelecommutingDay`, puis marque `SalaryMonth.is_generated` ; idempotent (garde sur `salary_recurring_id` + date). Rejoué par la tâche de fond via `check_and_generate_pending_salaries`.

## Auth et sécurité

- Un seul admin : `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH` (bcrypt), surchargeables via `PUT /admin/profile` (stocké dans `system_settings`). JWT HS256, durée `ACCESS_TOKEN_EXPIRE_MINUTES` (60).
- `POST /auth/token` protégé par `LoginRateLimiter` (`core/login_rate_limit.py`, 5 tentatives / 15 min par défaut).
- `config.py` refuse une `SECRET_KEY` placeholder ou < 32 caractères dans **tous** les environnements sauf `test` ; en `APP_ENV=prod` il refuse aussi hash admin placeholder et CORS `*`.
- Changer l'identifiant ou le mot de passe via `PUT /admin/profile` exige `current_password` (400 sinon, jamais 401/403 : le client API déconnecte sur ces codes) ; mot de passe ≥ 8 caractères.
- JWT : PyJWT (`jwt`), HS256.
- Ne jamais commiter `*.db` (ignorés par `.gitignore`).

## Tests

- `PYTHONPATH=. python3.11 -m pytest tests -q` depuis `backend/` (183 tests, ~13 s). `make test` détecte l'interpréteur (venv, sinon python3.12/3.11) ; `venv_new` est en Python 3.14 sans pytest.
- Fixtures (`tests/conftest.py`) : `db_session` (SQLite temporaire par test, `Base.metadata.create_all`) et `client` (TestClient, override de `get_db` et `get_current_user` → `"admin"`, rate limiter réinitialisé). Vérifier l'état en base après l'appel API.
- Un test par bug corrigé / fonctionnalité ajoutée, nommé `tests/test_<domaine>.py`.
