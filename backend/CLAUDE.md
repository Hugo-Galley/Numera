# Backend — conventions (FastAPI / SQLAlchemy 2 / Pydantic v2)

Complète le `CLAUDE.md` racine. Procédures pas-à-pas : skill `numera-backend`. Routes et schéma de données : `ARCHITECTURE.md`.

## Structure et cycle de vie

- `app/main.py` : `lifespan` → `run_migrations()` (Alembic ; un échec **bloque le démarrage**, pas de `stamp head` automatique) + `seed_all()` (catégories par défaut + profils ETF système), sauf si `APP_ENV=test`. Lance aussi `recurring_transactions_task` : boucle asynchrone (1er passage après 10 s, puis toutes les heures) qui appelle `generate_recurring_transactions`, `check_and_generate_pending_salaries`, `refresh_held_prices` (cours des titres détenus) et `refresh_held_etf_profiles` (composition des ETF détenus, au plus une fois par semaine) et `run_notifications` (nouvelles alertes du Centre d'Actions + résumé du dimanche vers ntfy / Telegram, si activés).
- Routers : tous dans `protected_routers` (`Depends(get_current_user)`) sauf `health` et `auth`. `controllers/analytics/` agrège 7 sous-routers sous le préfixe `/analytics` (`__init__.py`), plus `analytics/diversity.py` enregistré séparément.
- `controllers/deps.py` : `get_db` (session par requête) et `get_current_user` (décode le JWT, compare `sub` à `admin_username` lu dans `system_settings` avec repli sur `settings.ADMIN_USERNAME`).
- Sessions de **test** : `conftest.py` surcharge `get_db` (deux chemins : `app.db.session` et `app.controllers.deps`) et `get_current_user`.

## Couches (cf. `ARCHITECTURE.md` § Couches backend)

- Router (`controllers/`) : signature HTTP + un appel de service, rien d'autre. Service (`services/`) : logique, `commit`, erreurs métier. Repository (`repositories/`) : requêtes, sans `commit`. Calcul pur : `domain/`. Appel réseau : `integrations/`.
- `tests/test_architecture.py` refuse toute nouvelle violation (dont un import vers un module `app.*` introuvable : un import relatif déplacé tel quel, souvent avalé par un `except`). `scripts/check_code_size.py` refuse tout fichier > 400 lignes ou fonction > 80. Les deux baselines ne font que diminuer ; un déplacement à l'identique renomme la clé sans augmenter la valeur.
- Déplacer du code = mettre à jour tous les importeurs (absolus, relatifs, imports locaux, tests et `monkeypatch.setattr` sur l'ancien module), sans ré-export.

## Règles de code

- Typer arguments et retours. Logger : `from app.core.logging import get_logger; logger = get_logger(__name__)` (jamais de `print`, jamais de JWT/hash/secret dans les logs).
- Erreurs : dans un service, lever `NotFoundError` / `BusinessRuleError` (422) / `ConflictError` / `InternalError` (`app.core.errors`, `code` + `context` optionnels pour une erreur structurée) ; jamais d'`HTTPException` hors de `controllers/`. Routers non migrés : `api_error(status, code, detail, context)` ou `HTTPException` (400 règle métier, 401/403 auth, 404 introuvable).
- Modèles : `Mapped` / `mapped_column`, index sur `account_id`, `date`, `merchant`, FK. Pas de logique métier dans les modèles → `app/services/` (ou `app/domain/` si calcul pur).
- Schémas : `Create` / `Update` / `Read` séparés, `ConfigDict(from_attributes=True)` sur les `Read`, `response_model` sur chaque endpoint (pas de `dict` brut).
- Les endpoints sont majoritairement **synchrones** (`def`) ; `async def` seulement quand on appelle du code async (`convert_amount`, `get_exchange_rates`, `services/market`, `services/etf_profiles`, génération récurrente).
- N+1 : relations en `lazy="selectin"` sur les modèles ; sinon `joinedload`/`selectinload` pour les listes.
- Dates : `app.core.time.utcnow_naive` (datetimes naïfs UTC en base).
- `tests/test_migrations.py` exige que `alembic upgrade head` produise exactement le schéma des modèles (`compare_metadata == []`) : tout changement de modèle sans migration fait échouer la suite. La révision `a9c1e4d7b2f6` rattrape les écarts historiques et ne fait rien sur une base créée par `create_all`.
- Schéma modifié → `cd backend && alembic revision --autogenerate -m "..."`, relire la migration, la committer. Les migrations s'appliquent seules au démarrage.

## Finance

- Montants **toujours positifs** en base ; `type` donne le sens. `apply_transaction_to_balance` : `Entree`/`Interets` ajoutent, `Sortie` retranche, `Solde Initial` **remplace** le solde. (`finance.py`)
- Toute mutation de transaction (create / update / delete / bulk / liaison de virement / import) → `recalculate_running_balances(db, account_id)`, définie dans **`app/services/balances.py`**. Recalcul intégral par ordre chronologique ; **ne commit pas** (`flush`) : l'appelant commit après son dernier recalcul (`tests/test_balances_service.py` relit les soldes dans une session neuve).
- Devises : `await convert_amount(...)` / `await get_exchange_rates()` (`integrations/currency.py`). Stocker `amount` (devise du compte) et garder `original_amount` + `currency`. Conversion datée par taux croisé via l'EUR pour toute paire ; sans taux exploitable `CurrencyConversionError` (→ HTTP 422 via le handler de `main.py`), **jamais** de repli 1:1.
- Positions : `portfolio_holdings` est **dérivé**. Après toute mutation d'opération d'investissement ou de l'inventaire Point Zéro (`holding_baseline_items`), appeler `await rebuild_holdings(db, account_id)` (`services/holdings/rebuild.py`) : inventaire + opérations sur titres postérieures à `accounts.holdings_baseline_date`, PRU en moyenne pondérée frais inclus (devise de la position), vente sans effet sur le PRU, `cost_basis_eur` aux taux historiques. Ne jamais écrire `quantity`/`buy_price_avg` directement.
- Valorisation : `services/portfolio/compute.py::compute_portfolio` (étapes dans `services/portfolio/`, XIRR/TWR dans `domain/performance.py`) (valeur = positions × cours + espèces, plus-values latente/réalisée, XIRR/TWR, courbe, rapprochement) ; un compte `investissement` avec positions n'est plus valorisé par snapshot (`uses_positions`). `services/holdings/replay.py::replay_account` rejoue aussi les ventes (plus-value réalisée) et les variations de quantité.
- Cours : `get_market_quotes(symbols, db=db)` enregistre chaque cotation dans `security_prices` et renvoie le dernier cours stocké (`stale=True`) si Yahoo échoue ; `get_price_on(db, ticker, date)` pour un cours historique.
- Solde Initial : un seul par compte et chronologiquement premier ; contrôle centralisé dans `validate_solde_initial` (`controllers/transactions.py`) pour create/update, et dans l'import.
- SQLite : `PRAGMA foreign_keys=ON` est posé à chaque connexion (`db/session.py`, aussi dans `conftest.py`) : les `ondelete` sont effectifs. Une FK sans `ondelete` (ex. `salary_configs`) oblige à mettre la référence à `NULL` avant de supprimer la cible.
- Virements internes : `is_transfer`, `linked_transaction_id`, `is_transfer_ignored` ; un virement vers un compte `investissement` peut être lié à une `investment_transaction` (`linked_investment_transaction_id`). Les KPI « dépenses réelles » excluent ces transferts.
- Marchés : `integrations/yahoo_finance.py` interroge **Yahoo Finance** (`query2.finance.yahoo.com`, via `httpx`) pour la recherche de titres et les cotations, orchestrées par `services/market/` (`quotes` : cache, stockage dans `security_prices` via `repositories/security_prices.py` ; `search` ; `suggestions`) ; `services/etf_profiles.py` y récupère (via `yahoo_finance.fetch_composition`) la composition des ETF (secteurs + top 10 via `quoteSummary`/`topHoldings`, avec cookie + crumb ; jamais les pays), source par champ dans `etf_profiles.composition_sources` (`yahoo` / `preset` / `manual`). Ce sont, avec Frankfurter, les seuls appels réseau sortants, plus les notifications push que l'utilisateur active lui-même (`services/notifications.py (canaux : integrations/notifications.py)` : serveur ntfy configuré, `api.telegram.org`).
- Salaire : `services/salary_generation.py::generate_salary_transactions` (montant : `domain/salary.py::salary_amount`) crée une seule transaction `Entree` « Salaire » (`net_salary − nb_jours_TT × ticket_employee_share`, aucune transaction TR) à partir de `SalaryConfig` et des `TelecommutingDay`, puis marque `SalaryMonth.is_generated` ; idempotent (garde sur `salary_recurring_id` + date). Rejoué par la tâche de fond via `check_and_generate_pending_salaries`, qui regénère aussi un mois des 31 derniers jours marqué généré mais sans entrée de salaire (`is_salary_recorded`).

## Auth et sécurité

- Un seul admin : `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH` (bcrypt), surchargeables via `PUT /admin/profile` (stocké dans `system_settings`). JWT HS256, durée `ACCESS_TOKEN_EXPIRE_MINUTES` (60).
- `POST /auth/token` protégé par `login_rate_limiter` (`core/login_rate_limit.py`, 5 tentatives / 15 min par défaut, clé `client_key(request, username)` ; la passkey partage ce limiteur, le TOTP a `totp_rate_limiter`).
- Double authentification TOTP (routes `controllers/totp.py`, calcul, `is_enabled` et `create_mfa_token` dans `core/totp.py`) : si active, `POST /auth/token` ne renvoie qu'un `mfa_token` ; la session s'obtient via `POST /auth/totp/login`. Pas exigée pour la passkey.
- `config.py` refuse une `SECRET_KEY` placeholder ou < 32 caractères dans **tous** les environnements sauf `test` ; en `APP_ENV=prod` il refuse aussi hash admin placeholder et CORS `*`.
- Changer l'identifiant ou le mot de passe via `PUT /admin/profile` exige `current_password` (400 sinon, jamais 401/403 : le client API déconnecte sur ces codes) ; mot de passe ≥ 8 caractères.
- JWT : PyJWT (`jwt`), HS256. `POST /auth/refresh` renouvelle un jeton de session encore valide (jamais un jeton MCP) en gardant `auth_time` ; refusé (401) au-delà de `SESSION_MAX_HOURS` (12 h) depuis la connexion. Le front l'appelle quand il reste moins de 15 min (`lib/api.ts`).
- Ne jamais commiter `*.db` (ignorés par `.gitignore`).

## Tests

- `PYTHONPATH=. python3.11 -m pytest tests -q` depuis `backend/` (~910 tests, ~1 min 45). `make test` détecte l'interpréteur (venv, sinon python3.12/3.11) ; `venv_new` est en Python 3.14 sans pytest.
- Fixtures (`tests/conftest.py`) : `db_session` (SQLite temporaire par test, `Base.metadata.create_all`) et `client` (TestClient, override de `get_db` et `get_current_user` → `"admin"`, rate limiter réinitialisé). Vérifier l'état en base après l'appel API.
- Un test par bug corrigé / fonctionnalité ajoutée, nommé `tests/test_<domaine>.py`.
- `tests/test_analytics_snapshots.py` fige la sortie de toutes les routes analytics (démo à date figée), `tests/test_portfolio_snapshots.py` celle des routes du portefeuille (même démo + un compte titres avec Point Zéro) : un écart est un bug, ne jamais régénérer les instantanés pour faire passer le test (procédure : skill `numera-testing`).
