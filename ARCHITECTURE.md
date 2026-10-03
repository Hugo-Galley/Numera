# ARCHITECTURE.md

## Objectif

Decrire l'architecture actuelle du depot pour permettre a un humain ou a un agent IA de modifier le projet sans deviner l'organisation reelle.

## Vue D'ensemble

- Frontend: SPA React 18 + Vite + TypeScript + Tailwind + Recharts.
- Backend: FastAPI + SQLAlchemy + Alembic + Pydantic v2.
- Base: SQLite locale dans `backend/data/suivi_budget.db` en dev Docker.
- Auth: mono-admin JWT, routes metier protegees.
- Orchestration: `infra/docker-compose.yml` (dev : `backend`, `frontend`, `backup`) ; `docker-compose.prod.yml` (prod : + service optionnel `mcp-server`, profil `mcp`; frontend Nginx publié sur `127.0.0.1:8082`, proxy `/api/` → `backend:8001`).
- Services externes (seuls appels sortants) : Frankfurter (taux de change) et Yahoo Finance (recherche/cotations de titres, profils ETF).
- Serveur MCP optionnel dans `mcp-server/` (voir `mcp-server/README.md`).

Flux principal:

1. L'utilisateur se connecte via `/login`.
2. Le frontend stocke le token dans `localStorage`.
3. `apiFetch()` ajoute le bearer token aux appels JSON.
4. FastAPI valide l'utilisateur via `get_current_user`.
5. Les endpoints lisent/ecrivent SQLite via SQLAlchemy.
6. Les agregats finance sont calcules par le backend et renvoyes prets a afficher.

## Arborescence Reelle

```text
backend/
  alembic/              migrations
  app/
    api/                endpoints REST
    core/               config, finance, currency, errors, migrations, security, logging,
                        login_rate_limit, recurring, salary, market_data, etf_analyzer, seeds*
    db/                 session SQLAlchemy, system_settings (get_setting/set_setting)
    models/             modeles ORM
    schemas/            schemas Pydantic
  data/                 SQLite dev
  scripts/              backup, backup_scheduler, restore, seed_demo, backfill
  tests/                pytest backend (85 tests)
frontend/
  src/
    components/         layout, ui (shadcn), dashboard (+ tabs/), investments, settings, tools, analytics
    lib/                apiFetch, utils, countries
    types/              types partages (diversity.ts)
    lib/                apiFetch, utils, countries
    types/              types partages (diversity.ts)
    pages/              routes principales
    providers/          AuthProvider, UIProvider
mcp-server/             serveur MCP (server_api.py = proxy API, server_sqlite.py = accès SQLite direct)
infra/
  docker-compose.yml (dev)
docker-compose.prod.yml, Makefile, setup.sh, install.sh
```

## Backend

### Cycle De Vie

- `backend/app/main.py` cree l'application FastAPI.
- Au startup, `run_migrations()` lance Alembic sauf en environnement `test`.
- `seed_all()` insere les categories par defaut et les profils ETF systeme sauf en `test`.
- Une tache de fond (`recurring_transactions_task`, toutes les heures, 1er passage apres 10 s) genere les transactions recurrentes et les salaires en attente.
- `GET /health` et `POST /auth/token` sont publics.
- Les autres routeurs sont inclus avec `Depends(get_current_user)`.

### Modules API

- `auth.py`: login OAuth2 password et génération JWT.
- `accounts.py`: CRUD comptes, suppression logique par `active=False`.
- `categories.py`: CRUD catégories avec limites mensuelles/annuelles.
- `transactions.py`: CRUD transactions, recherche marchands, bulk update, recalcul soldes.
- `investment_transactions.py`: opérations `versement`, `retrait`, `dividende`.
- `balance_snapshots.py`: snapshots de valeur et définition de point zéro.
- `imports.py`: preview/commit CSV Numbers.
- `exports.py`: export CSV compatible Numbers.
- `analytics/` (package, prefixe `/analytics`): `metrics` (tags, depenses par categorie, top marchands, kpi-history, timeseries, calendar), `budget` (budget, budget-alerts), `investments` (investissements, performance, allocations, patrimoine, simulation), `reports` (cashflow-projection, monthly-report, money-flow, sankey), `subscriptions`, `insights`, `audit` (audit + Centre d'Actions `/actions`), `diversity` (scanner de diversification), `utils`.
- `holdings.py`: positions titres (`portfolio_holdings`), suggestions depuis les notes, baseline.
- `market.py`: recherche, validation et cotation de titres (Yahoo Finance).
- `etf_profiles.py`: profils ETF (pays/secteurs/top holdings), auto-decomposition en ligne.
- `savings_goals.py`: objectifs d'épargne calculés par mot-clé.
- `categorization_rules.py`: règles locales d'auto-catégorisation basées sur le commerçant.
- `recurring_transactions.py`: abonnements et transactions récurrentes avec génération automatique.
- `tags.py`: tags transversaux personnalisables.
- `salary.py`: configuration de salaire, jours de télétravail (TT) et génération des transactions associées.
- `merchants.py`: gestion des marchands canoniques et de leurs alias de normalisation.
- `admin.py`: profil admin (nom/mot de passe, stockes dans `system_settings`) et reset database.
- `health.py`: healthcheck public.

## Frontend

Routes dans `frontend/src/App.tsx`:

- `/login`: authentification.
- `/`: dashboard (organisé avec des onglets : Overview, History, Budgets, Insights, Investments, Merchants, Projections, Subscriptions).
- `/accounts`: liste des comptes (incluant la bannière de validation périodique).
- `/accounts/:id`: détail compte courant/épargne/investissement.
- `/savings`: objectifs d'épargne.
- `/investments`: vue globale investissements.
- `/comparison`: comparaison mensuelle.
- `/calendar`: calendrier financier.
- `/recurring`: abonnements et charges fixes.
- `/report`: rapport mensuel intelligent (page `MonthlyReport.tsx`) avec export PDF et onglets d'analyse des flux.
- `/audit`: Centre d'Actions (audit d'integrite, alertes budget, suggestions de regles) — voir `docs/ACTION_CENTER.md`.
- `/tools`: gestion du salaire et calendrier de télétravail (TT).
- `/settings`: configuration, import CSV, gestion des virements, règles d'auto-catégorisation, tags, gestion des marchands canoniques et actions admin.

Principes:

- `AuthProvider` gere le token et l'etat de connexion.
- `ProtectedRoute` bloque les pages applicatives sans token.
- `UIProvider` porte l'etat UI global, dont le mode confidentialite.
- `apiFetch()` centralise les appels JSON et redirige vers `/login` en cas de `401` (ou `403` hors `/auth/token`). `API_BASE` = `http://localhost:8001` sur localhost, `/api` ailleurs.
- Les uploads CSV n'utilisent pas `apiFetch()` pour laisser le navigateur definir le multipart boundary (le `fetch` direct de `ImportTab.tsx` n'envoie actuellement pas le Bearer : bug connu).

## Modele De Donnees

### `accounts`

Champs principaux: `id`, `name`, `type`, `currency`, `created_at`, `active`, `color`, `asset_class`, `sector`, `geographic_zone`, `institution`, `fonds_euros_pct`, `fonds_investis_pct` (assurance-vie), `is_main`, `last_verified_at`. La suppression API est logique (`active=False`).

Types connus: `courant`, `epargne`, `investissement`.

### `categories`

Champs: `id`, `name`, `icon`, `color`, `type`, `monthly_limit`, `annual_limit`, `group`.

`name` est unique. Les limites alimentent les alertes budget.

### `transactions`

Champs: `id`, `account_id`, `date`, `month_label`, `type`, `merchant`, `merchant_id`, `category_id`, `amount`, `currency`, `original_amount`, `running_balance`, `note`, `is_recurring`, `recurring_transaction_id`, `is_subscription_ignored`, `custom_icon`, `custom_color`, `is_transfer`, `is_transfer_ignored`, `is_duplicate_ignored`, `linked_transaction_id`, `linked_investment_transaction_id`.

`amount` est le montant converti dans la devise du compte. `original_amount` et `currency` gardent la saisie d'origine. Les champs de liaison permettent de connecter des virements internes ou de rattacher une transaction à sa règle récurrente génératrice.

### `investment_transactions`

Champs: `id`, `account_id`, `date`, `type`, `amount`, `currency`, `original_amount`, `note`, `asset_class`, `sector`, `geographic_zone`, `ticker`, `isin`, `quantity`, `unit_price`, `etf_profile_id`, `is_transfer`, `is_transfer_ignored`, `linked_transaction_id`, `recurring_transaction_id`.

Types connus: `versement`, `retrait`, `dividende`.

### `balance_snapshots`

Champs: `id`, `account_id`, `date`, `current_value`, `note`, `is_zero_point`.

Un point zéro sert de base de performance pour un compte.

### Autres Tables

- `portfolio_holdings`: positions titres par compte (`account_id`, `ticker`, `isin`, `asset_name`, `quantity`, `buy_price_avg`, `currency`, `etf_profile_id`).
- `etf_profiles`: profils ETF (`name`, `ticker`, `isin`, `aliases`, `countries`, `sectors`, `top_holdings` en JSON texte, `is_system`).
- `system_settings`: paires cle/valeur (ex. `admin_username`, `admin_password_hash`).
- `imports_log`: journal d'import CSV.
- `historical_exchange_rates`: cache de taux historiques.
- `savings_goals`: objectifs d'épargne (`name`, `target_amount`, `keyword`, `deadline`, `account_id`, `category_id`, `icon`, `color`).
- `categorization_rules`: règles d'auto-catégorisation locale basées sur des patterns de commerçants (`id`, `pattern`, `category_id`, `transaction_type`, `merchant_name`, `priority`).
- `recurring_transactions`: définitions d'abonnements/charges fixes récurrentes (`id`, `account_id`, `name`, `type`, `amount`, `currency`, `category_id`, `frequency`, `day_of_month`, `start_date`, `end_date`, `excluded_months`, `last_generated_date`, `is_active`, `auto_generate`, `note`, `asset_class`, `sector`, `geographic_zone`, `ticker`, `isin`, `quantity`, `unit_price`, `etf_profile_id`).
- `tags`: tags transversaux personnalisés (`id`, `name`, `color`).
- `transaction_tags`: table d'association many-to-many (`transaction_id`, `tag_id`).
- `merchants`: marchands canoniques (`id`, `name`, `category_id`, `icon`, `color`).
- `merchant_aliases`: alias et libellés bancaires d'origine associés aux marchands canoniques (`id`, `merchant_id`, `label`).
- `salary_configs`: configuration de salaire pour la génération TR/TT (`id`, `salary_account_id`, `ticket_account_id`, `net_salary`, `ticket_value`, `ticket_employee_share`, `salary_category_id`, `ticket_category_id`, `salary_recurring_id`, `ticket_recurring_id`, `is_active`).
- `salary_months`: statut de génération des salaires par mois (`id`, `salary_config_id`, `month_label`, `salary_date`, `ticket_date`, `is_generated`, `generated_at`).
- `telecommuting_days`: jours de télétravail déclarés par mois (`id`, `salary_config_id`, `date`, `month_label`).
- `dismissed_insights`: insights/anomalies de dépenses masqués par l'utilisateur (`id`, `title`, `dismissed_at`; `title` stocke l'`id` stable d'une insight/action masquee).

## Routes Principales

### Public

- `GET /health`
- `POST /auth/token` (limite de tentatives par client/utilisateur)

### CRUD Et Donnees

- `/accounts`
- `/categories`
- `/transactions`
- `/investment-transactions`
- `/balance-snapshots`
- `/goals`
- `/categorization-rules`
- `/recurring-transactions` (+ `POST /trigger`)
- `/tags`
- `/merchants` (+ aliases, `auto-normalize`, `suggestions/unnormalized`)
- `/holdings`, `/etf-profiles`, `/market` (search, validate, quote)
- `/salary` (config, months, telecommuting, summary, generate)
- `/admin` (profile, reset-database)

### Import Export

- `POST /import/preview`
- `POST /import/commit`
- `GET /export/transactions.csv`

### Analytics

- `GET /analytics/budget`
- `GET /analytics/actions`, `POST /analytics/actions/dismiss`, `GET /analytics/audit`, `GET /analytics/audit/{issue_id}`
- `GET /analytics/cashflow-projection`, `GET /analytics/calendar`, `GET /analytics/patrimoine-allocation`
- `GET /analytics/asset-allocation/suggestions`, `GET /analytics/diversity-scanner`
- `POST /analytics/insights/dismiss`, `POST /analytics/subscriptions/ignore`, `GET /analytics/tags`
- `GET /analytics/expenses-by-category`
- `GET /analytics/top-merchants`
- `GET /analytics/investments`
- `GET /analytics/investments/{account_id}`
- `GET /analytics/investments/{account_id}/performance-history`
- `GET /analytics/subscriptions`
- `GET /analytics/kpi-history`
- `GET /analytics/investments-allocation`
- `GET /analytics/investments-allocation-advanced`
- `GET /analytics/timeseries`
- `GET /analytics/budget-alerts`
- `GET /analytics/insights`
- `GET /analytics/wealth-simulation`
- `GET /analytics/sankey`
- `GET /analytics/money-flow`
- `GET /analytics/monthly-report`

## Regles De Calcul

- `Entree` et `Interets` augmentent le solde.
- `Sortie` diminue le solde.
- `Solde Initial` remplace le solde courant par le montant de depart.
- Pour une periode filtree, `Solde Initial` est exclu des revenus.
- Les depenses reelles excluent les transferts internes vers `Investissement` et `Epargne` quand le calcul le demande.
- Le taux d'epargne utilise les depenses reelles et est borne entre `-100` et `100`.
- Le burn rate est calcule sur les jours ecoules du mois courant ou le nombre de jours du mois passe.
- Les investissements utilisent les snapshots pour la valeur actuelle et les operations pour les flux.

## Import CSV

Pipeline:

1. Lecture UTF-8 avec BOM tolere.
2. Detection delimiter `,`, `;` ou tabulation.
3. Normalisation des headers avec `HEADER_ALIASES`.
4. Validation des colonnes obligatoires: `Date`, `Mois`, `Type`, `Commercant`, `Categorie`, `Montant`.
5. Parsing dates et montants francais/anglais.
6. Normalisation type via `normalize_transaction_type()`.
7. Mapping manuel categories, creation optionnelle des categories manquantes.
8. Detection doublons.
9. Insertion avec solde courant, journal `imports_log`, puis `recalculate_running_balances` si au moins une ligne est importee.

## Multi-Devise

- Taux courants: Frankfurter, cache memoire 6h.
- Taux historiques: Frankfurter, cache SQLite dans `historical_exchange_rates`.
- Fallback offline EUR: `EUR=1.0`, `USD=1.08`, `GBP=0.84`, `CHF=0.95`.
- Conversion vers EUR: `amount / rate` quand `rate` represente `1 EUR = X devise`.

## Sauvegardes

- Service Docker `backup` lance `backend/scripts/backup_scheduler.py`.
- Source: `backend/data/suivi_budget.db` montee dans `/app/data`.
- Destination: `backups/` a la racine via `/app/backups`.
- Variables: `BACKUP_KEY`, `BACKUP_INTERVAL_SECONDS`, `RETENTION_DAYS` selon scripts.
- Commandes: `make backup-now`, `make backup-restore FILE=...` (le compose dev ne definit pas `RETENTION_DAYS` ; defaut 7 jours dans les scripts).

La cle `BACKUP_KEY` est indispensable pour restaurer les backups chiffres.
