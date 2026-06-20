# ARCHITECTURE.md

## Objectif

Decrire l'architecture actuelle du depot pour permettre a un humain ou a un agent IA de modifier le projet sans deviner l'organisation reelle.

## Vue D'ensemble

- Frontend: SPA React 18 + Vite + TypeScript + Tailwind + Recharts.
- Backend: FastAPI + SQLAlchemy + Alembic + Pydantic v2.
- Base: SQLite locale dans `backend/data/suivi_budget.db` en dev Docker.
- Auth: mono-admin JWT, routes metier protegees.
- Orchestration: `infra/docker-compose.yml` avec `backend`, `frontend`, `backup`.

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
    core/               config, finance, currency, errors, migrations, security
    db/                 session SQLAlchemy
    models/             modeles ORM
    schemas/            schemas Pydantic
  data/                 SQLite dev
  scripts/              backup, restore, seed demo
  tests/                pytest backend
frontend/
  src/
    components/layout/  AppLayout, Sidebar, Omnibox, ProtectedRoute
    components/ui/      composants UI
    lib/                apiFetch, utils, countries
    pages/              routes principales
    providers/          AuthProvider, UIProvider
infra/
  docker-compose.yml
```

## Backend

### Cycle De Vie

- `backend/app/main.py` cree l'application FastAPI.
- Au startup, `run_migrations()` lance Alembic sauf en environnement `test`.
- `seed_default_categories()` insere les categories par defaut sauf en `test`.
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
- `analytics.py`: tous les KPI, distributions, timeseries, allocations, alertes, insights, rapport mensuel, Sankey et simulation de patrimoine.
- `savings_goals.py`: objectifs d'épargne calculés par mot-clé.
- `categorization_rules.py`: règles locales d'auto-catégorisation basées sur le commerçant.
- `recurring_transactions.py`: abonnements et transactions récurrentes avec génération automatique.
- `tags.py`: tags transversaux personnalisables.
- `salary.py`: configuration de salaire, jours de télétravail (TT) et génération des transactions associées.
- `merchants.py`: gestion des marchands canoniques et de leurs alias de normalisation.
- `admin.py`: reset database.
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
- `/recurring-transactions`: abonnements et charges fixes.
- `/monthly-report`: rapport mensuel intelligent avec export PDF et onglets d'analyse des flux.
- `/tools`: gestion du salaire et calendrier de télétravail (TT).
- `/settings`: configuration, import CSV, règles d'auto-catégorisation, tags, gestion des marchands canoniques et actions admin.

Principes:

- `AuthProvider` gere le token et l'etat de connexion.
- `ProtectedRoute` bloque les pages applicatives sans token.
- `UIProvider` porte l'etat UI global, dont le mode confidentialite.
- `apiFetch()` centralise les appels JSON et redirige vers `/login` en cas de `401`.
- Les uploads CSV n'utilisent pas `apiFetch()` pour laisser le navigateur definir le multipart boundary.

## Modele De Donnees

### `accounts`

Champs principaux: `id`, `name`, `type`, `currency`, `created_at`, `active`, `color`, `asset_class`, `sector`, `geographic_zone`, `is_main`, `last_verified_at`.

Types connus: `courant`, `epargne`, `investissement`.

### `categories`

Champs: `id`, `name`, `icon`, `color`, `type`, `monthly_limit`, `annual_limit`.

`name` est unique. Les limites alimentent les alertes budget.

### `transactions`

Champs: `id`, `account_id`, `date`, `month_label`, `type`, `merchant`, `merchant_id`, `category_id`, `amount`, `currency`, `original_amount`, `running_balance`, `note`, `is_recurring`, `recurring_transaction_id`, `is_subscription_ignored`, `custom_icon`, `custom_color`, `is_transfer`, `is_transfer_ignored`, `linked_transaction_id`, `linked_investment_transaction_id`.

`amount` est le montant converti dans la devise du compte. `original_amount` et `currency` gardent la saisie d'origine. Les champs de liaison permettent de connecter des virements internes ou de rattacher une transaction à sa règle récurrente génératrice.

### `investment_transactions`

Champs: `id`, `account_id`, `date`, `type`, `amount`, `currency`, `original_amount`, `note`, `asset_class`, `sector`, `geographic_zone`.

Types connus: `versement`, `retrait`, `dividende`.

### `balance_snapshots`

Champs: `id`, `account_id`, `date`, `current_value`, `note`, `is_zero_point`.

Un point zéro sert de base de performance pour un compte.

### Autres Tables

- `imports_log`: journal d'import CSV.
- `historical_exchange_rates`: cache de taux historiques.
- `savings_goals`: objectifs d'épargne par mot-clé.
- `categorization_rules`: règles d'auto-catégorisation locale basées sur des patterns de commerçants (`id`, `merchant_pattern`, `category_id`).
- `recurring_transactions`: définitions d'abonnements/charges fixes récurrentes (`id`, `account_id`, `name`, `type`, `amount`, `currency`, `category_id`, `frequency`, `day_of_month`, `start_date`, `end_date`, `last_generated_date`, `is_active`, `auto_generate`, `note`, `asset_class`, `sector`, `geographic_zone`).
- `tags`: tags transversaux personnalisés (`id`, `name`, `color`).
- `transaction_tags`: table d'association many-to-many (`transaction_id`, `tag_id`).
- `merchants`: marchands canoniques (`id`, `name`, `category_id`, `icon`, `color`).
- `merchant_aliases`: alias et libellés bancaires d'origine associés aux marchands canoniques (`id`, `merchant_id`, `label`).
- `salary_configs`: configuration de salaire pour la génération TR/TT (`id`, `salary_account_id`, `ticket_account_id`, `net_salary`, `ticket_value`, `ticket_employee_share`, `salary_category_id`, `ticket_category_id`, `salary_recurring_id`, `ticket_recurring_id`, `is_active`).
- `salary_months`: statut de génération des salaires par mois (`id`, `salary_config_id`, `month_label`, `salary_date`, `ticket_date`, `is_generated`, `generated_at`).
- `telecommuting_days`: jours de télétravail déclarés par mois (`id`, `salary_config_id`, `date`, `month_label`).
- `dismissed_insights`: insights/anomalies de dépenses masqués par l'utilisateur (`id`, `title`, `dismissed_at`).

## Routes Principales

### Public

- `GET /health`
- `POST /auth/token`

### CRUD Et Donnees

- `/accounts`
- `/categories`
- `/transactions`
- `/investment-transactions`
- `/balance-snapshots`
- `/goals`
- `/categorization-rules`
- `/recurring-transactions`
- `/tags`

### Import Export

- `POST /import/preview`
- `POST /import/commit`
- `GET /export/transactions.csv`

### Analytics

- `GET /analytics/budget`
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
9. Insertion, journal `imports_log`, recalcul `running_balance`.

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
- Commandes: `make backup-now`, `make backup-restore FILE=...`.

La cle `BACKUP_KEY` est indispensable pour restaurer les backups chiffres.
