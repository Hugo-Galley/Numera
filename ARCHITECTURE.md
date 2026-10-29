# ARCHITECTURE.md

## Objectif

Decrire l'architecture actuelle du depot pour permettre a un humain ou a un agent IA de modifier le projet sans deviner l'organisation reelle.

## Vue D'ensemble

- Frontend: SPA React 18 + Vite + TypeScript + Tailwind + Recharts.
- Backend: FastAPI + SQLAlchemy + Alembic + Pydantic v2.
- Base: SQLite locale dans `backend/data/suivi_budget.db` en dev Docker.
- Auth: mono-admin JWT, routes metier protegees ; tokens MCP (`nmr_…`) acceptés à la place du JWT en lecture seule (`GET`), jamais sur `/admin`.
- Orchestration: `infra/docker-compose.yml` (dev : `backend`, `frontend`, `backup`) ; `docker-compose.prod.yml` (prod : + `mcp-server` en streamable-http ; frontend Nginx publié sur `127.0.0.1:8082`, proxy `/api/` → `backend:8001` et `/mcp` → `mcp-server:8100`).
- Services externes (seuls appels sortants) : Frankfurter (taux de change) et Yahoo Finance (recherche/cotations de titres, profils ETF).
- Serveur MCP dans `mcp-server/`, en lecture seule, connecté à Claude Code / Claude Desktop par token généré dans Paramètres → Sécurité (voir `mcp-server/README.md`).

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
    controllers/        routers REST (ex-api/)
    services/           cas d'usage : un module par domaine (accounts, transactions + transaction_writes/links,
                        imports, recurring, salary, month_review, reimbursements, transfers, loans, demo/, ...)
                        et analytics/{budget,cashflow}, audit, tax
    repositories/       requetes SQLAlchemy, un module par domaine (+ analytics/common)
    domain/             calculs purs : finance, transactions, transfers, csv_import, loans, salary,
                        savings_goals, recurring, exports
    integrations/       appels externes : currency (Frankfurter), yahoo_finance, notifications (ntfy, Telegram), logos, backup
    core/               transverse (config, errors, security, logging, login_rate_limit, totp, mcp_tokens, ...)
                        et metier herite, a migrer : wealth, budget_period, subscription_prices, tax*
                        (phase 3) ; portfolio, holdings, dividends (phase 4)
    db/                 session SQLAlchemy, system_settings (get_setting/set_setting)
    models/             modeles ORM
    schemas/            schemas Pydantic
  data/                 SQLite dev
  scripts/              backup, backup_scheduler, restore, seed_demo, backfill
  tests/                pytest backend (~840 tests, ~1 min 40)
frontend/
  src/
    components/         layout, ui (shadcn), dashboard (+ tabs/), investments, settings, classement, import, audit, tools, analytics
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

## Couches backend

Architecture en couches, migrée progressivement (plan : `docs/superpowers/plans/2026-10-28-architecture-en-couches.md`, conception : `docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md`). Domaine modèle : `accounts` (`controllers/accounts.py` → `services/accounts.py` → `repositories/accounts.py`). Phases 0-3 terminées : tous les routers d'écriture côté budget et administration, et les analytics (budget, Centre d'Actions, métriques, rapports, insights, abonnements, bilan annuel, investissements et projections, fiscalité) suivent ce modèle ; restent le portefeuille (phase 4 : `analytics/portfolio`, `dividends`, `diversity`, `holdings`, `investment_transactions`, `etf_profiles`, `market`, `core/portfolio`…) et le frontend (phase 5). Les chiffres analytics sont figés par `tests/test_analytics_snapshots.py`.

| Couche | Rôle | N'importe pas |
|---|---|---|
| `controllers/` | Controllers : HTTP, `Depends`, `Query`, appel d'un service. Ni `db.query`, ni `commit`, ni import de `app.models` (routers du portefeuille pas encore migrés). | un autre module `controllers.*` (sauf `controllers.deps` et son propre package) |
| `services/` | Cas d'usage : orchestration, **commit**, erreurs métier (`NotFoundError` 404, `InvalidOperationError` 400, `BusinessRuleError` 422, `ConflictError` 409, `InternalError` 500, `ExternalServiceError` 502, `ExternalTimeoutError` 504 de `core/errors.py`, traduites en HTTP par `main.py` avec le même corps qu'`api_error`). | `app.controllers`, `fastapi` |
| `repositories/` | Requêtes SQLAlchemy (`repositories/analytics/common.py` : `NET_AMOUNT`, `income_criterion`, `category_lines`…). Jamais de `commit` (`flush` permis). | `app.controllers`, `app.services`, `app.integrations`, `fastapi` |
| `domain/` | Calculs purs, sans Session (`domain/transactions.py` : `net_amount`, `tx_sample`, `tx_read` ; `budget`, `metrics`, `reports`, `insights`, `wrapped`, `projections`, `investments`, `budget_period`, `subscription_prices`, `tax`, `tax_rules`). | `app.controllers`, `app.services`, `app.repositories`, `app.integrations`, `app.db`, `sqlalchemy.orm`, `fastapi` |
| `integrations/` | Appels externes : `currency` (Frankfurter), `notifications` (canaux ntfy/Telegram), `logos`, `backup` (Yahoo : phase 4). | `app.controllers`, `app.services`, `app.repositories` |
| `core/` | Transverse (config, sécurité, logs, erreurs, rate limit, TOTP) et, pendant la migration, métier hérité. | `app.controllers` |

Garde-fous (cliquet, les baselines ne font que diminuer) : `backend/tests/test_architecture.py` + `architecture_baseline.txt` (règles ci-dessus, imports locaux compris, imports vers un module `app.*` introuvable, `commit()` dans `repositories/`) ; `scripts/check_code_size.py` + `scripts/code_size_baseline.json` (plafonds 400 lignes par fichier Python, 80 par fonction, 350 par fichier TS/TSX hors `components/ui`), lancé par `make check-size` / `make validate` et par pytest.

## Backend

### Cycle De Vie

- `backend/app/main.py` cree l'application FastAPI.
- Au startup, `run_migrations()` lance Alembic sauf en environnement `test`.
- `seed_all()` insere les categories par defaut et les profils ETF systeme sauf en `test`.
- Une tache de fond (`recurring_transactions_task`, toutes les heures, 1er passage apres 10 s) genere les transactions recurrentes et les salaires en attente, actualise cours et compositions d'ETF, puis envoie les notifications push (`services/notifications.py (canaux : integrations/notifications.py)::run_notifications`).
- `GET /health` et `POST /auth/token` sont publics.
- Mode démo (`DEMO_MODE=true`, package `services/demo/` : `guard`, `data`, `generator`) : base dédiée obligatoire (nom contenant « demo », vérifié par `config.py`). Au démarrage puis à chaque passage de la tâche de fond, `ensure_demo_data` efface la base et régénère un jeu fictif déterministe de 18 mois (4 comptes, virements liés, PEA avec cours synthétiques `security_prices.source = "demo"`, assurance-vie par relevés) s'il ne date pas du jour. La tâche de fond ne fait alors rien d'autre (ni cours réels, ni notifications) ; `get_market_quotes` sert les cours fictifs ; le middleware `demo_guard` renvoie 403 sur les écritures sensibles (`/admin/*`, TOTP, passkeys, notifications, logos, rafraîchissement d'ETF). Déploiement : `docker-compose.demo.yml` (`make demo`, port 8090, identifiants publics demo / demo).
- Les autres routeurs sont inclus avec `Depends(get_current_user)` : JWT de session, ou token MCP (`core/mcp_tokens.py` : empreinte SHA-256 dans `mcp_tokens`, refusé si révoqué, si `mcp_enabled` est faux ou pour toute méthode autre que `GET`/`HEAD`). Le router `/admin` ajoute `require_interactive_session` : 403 pour un token MCP.

### Modules API

- `auth.py`: login OAuth2 password et génération JWT ; `POST /auth/refresh` (renouvellement glissant d'un jeton de session valide, durée totale bornée par `SESSION_MAX_HOURS` via le claim `auth_time`, refusé aux jetons MCP) ; `GET /auth/whoami` (validation des identifiants, utilisé par le serveur MCP).
- `passkeys.py`: connexion WebAuthn (Face ID / Touch ID) en plus du mot de passe. `GET /auth/passkey/available` (public), `POST /auth/passkey/login/{options,verify}` (public, même limiteur de tentatives que le mot de passe), `GET/DELETE /auth/passkey` et `POST /auth/passkey/register/{options,verify}` (session interactive). Credentials en JSON dans `system_settings` (`webauthn_credentials`), défi dans un JWT signé de 5 min ; l'en-tête `Origin` doit figurer dans `CORS_ORIGINS` ou avoir le nom d'hôte de la requête (Host / X-Forwarded-Host) ; le RP ID en est le nom d'hôte.
- `totp.py` : double authentification TOTP (RFC 6238, Google Authenticator), exigée **uniquement après le mot de passe** (la passkey reste un facteur suffisant). Si elle est active, `POST /auth/token` renvoie `{mfa_required, mfa_token, token_type: "mfa"}` (JWT 5 min `purpose=totp`, sans `sub`, invalidé par un changement de mot de passe) au lieu d'une session ; `POST /auth/totp/login` (public, limiteur dédié) l'échange avec un code ou un code de secours contre la session. `GET /auth/totp/status`, `POST /auth/totp/{setup (mot de passe), enable (premier code), disable (mot de passe + code), recovery-codes (code)}` (session interactive). Stockage `system_settings` : `totp_secret`, `totp_pending_secret`, `totp_last_step` (anti-rejeu), `totp_recovery_codes` (10 empreintes SHA-256, usage unique). Calcul dans `core/totp.py`, QR code SVG via `segno`.
- `accounts.py`: CRUD comptes, suppression logique par `active=False` (logique dans `services/accounts.py`, requêtes dans `repositories/accounts.py`). Solde affiché : `services/accounts.py::account_balance` (dernier relevé ou dernier `running_balance`, le plus récent des deux) ; un compte `credit` vaut −capital restant dû.
- `loans.py`: crédits (`/loans`). Un crédit = un compte `credit` + une ligne `loans`, créés et supprimés ensemble. Échéancier, capital restant dû et simulation de remboursement anticipé calculés par `domain/loans.py` (`loan_remaining` : `services/loans.py`) (fonctions pures).
- `categories.py`: CRUD catégories avec limites mensuelles/annuelles.
- `transactions.py`: CRUD transactions, recherche marchands, bulk update, suppression groupée (`POST /transactions/bulk-delete`, une seule transaction SQL puis un recalcul par compte), recalcul soldes.
- `investment_transactions.py`: opérations `versement`, `retrait`, `achat`, `vente`, `dividende`, `frais` ; toute mutation appelle `rebuild_holdings`. `POST /investment-transactions/link-dividends?account_id=&dry_run=` rattache les anciens dividendes sans titre à une position d'après leur libellé.
- `balance_snapshots.py`: snapshots de valeur et définition de point zéro.
- `imports.py`: preview/commit CSV Numbers.
- `exports.py`: export CSV compatible Numbers.
- `analytics/` (package, prefixe `/analytics`): `metrics` (tags, depenses par categorie, top marchands, kpi-history, timeseries, calendar) : calculs dans le package `services/analytics/metrics/` (un module par route), requêtes `repositories/analytics/metrics.py`, formules `domain/metrics.py`, `budget` (budget, budget-alerts, resilience : calculs dans le package `services/analytics/budget/` (`summary` : étapes de `compute_budget`, `alerts`, `resilience`), requêtes `repositories/analytics/budget.py`, formules `domain/budget.py`), `investments` (investissements, performance, allocations, patrimoine, simulation : package `services/analytics/investments/` (`summary`, `flows`, `account`, `allocation`, `projections`), requêtes `repositories/analytics/investments.py`, projections pures (FIRE, prévision, Monte-Carlo) dans `domain/projections.py`, répartitions dans `domain/investments.py`), `reports` (cashflow-projection, monthly-report, money-flow, sankey : package `services/analytics/reports/`, requêtes `repositories/analytics/reports.py`, formules `domain/reports.py`), `subscriptions`, `insights` (calculs dans `services/analytics/subscriptions.py` et `insights.py`), `audit` (audit + Centre d'Actions `/actions`, calculé par `services/audit/` : registre `RULES` d'un module par règle dans `rules/`, audit des données dans `data_audit.py`), `diversity` (scanner de diversification), `dividends` (dividendes en EUR : totaux, par mois / année / titre, rendements), `portfolio` (valeur calculée, plus-values, XIRR/TWR, rapprochement ; synthèse `services/analytics/portfolio.py::portfolio_overview`, aussi appelée par la prévision de patrimoine) ; requêtes partagées dans `repositories/analytics/common.py` (dont `income_criterion`, définition unique du revenu). Valeur d'un compte / patrimoine : `services/wealth.py`.
- `holdings.py`: positions titres (`portfolio_holdings`, lecture seule hors métadonnées), inventaire Point Zéro (`POST /holdings/baseline` avec `date` optionnelle ; `POST`/`PUT`/`DELETE /holdings` éditent une ligne d'inventaire), suggestions depuis les notes. Chaque position porte `price_date` / `price_stale`.
- `market.py`: recherche, validation et cotation de titres (Yahoo Finance).
- `etf_profiles.py`: profils ETF (pays/secteurs/top holdings). Composition récupérée sur Yahoo Finance (`quoteSummary`, module `topHoldings` : secteurs + top 10, jamais les pays) : `POST /etf-profiles/auto-decompose` (création), `POST /etf-profiles/{id}/refresh` (502 si Yahoo injoignable), `POST /etf-profiles/refresh-held` (tous les profils détenus). La tâche de fond actualise les profils détenus au plus une fois par semaine.
- `savings_goals.py`: objectifs d'épargne calculés par mot-clé.
- `categorization_rules.py`: règles locales d'auto-catégorisation basées sur le commerçant.
- `recurring_transactions.py`: abonnements et transactions récurrentes avec génération automatique.
- `tags.py`: tags transversaux personnalisables.
- `salary.py`: configuration de salaire, jours de télétravail (TT) et génération des transactions associées.
- `work_time.py`: taux horaire net = `net_salary × 12 ÷ (work_days_per_year × work_hours_per_day)` (218 j × 7 h par défaut), base du prix en heures de travail.
- `merchants.py`: gestion des marchands canoniques et de leurs alias de normalisation.
- `admin.py`: profil admin (nom/mot de passe, `mcp_enabled`, `privacy_on_start` = ouvrir l'app montants masqués, clé `ui.privacy_on_start`, stockes dans `system_settings`), journal des connexions (`GET /admin/login-events?limit=`, table `login_events`), `POST /admin/logout-all` (pousse `auth_valid_after` : toutes les sessions, y compris la courante, sont refusées ; tokens MCP non concernés), état des sauvegardes (`GET /admin/backup/status`, `integrations/backup.py::backup_status` : fichiers `suivi_budget_*` et `status.json` de `BACKUP_DIR`, `stale` au-delà de 2 jours), tokens MCP (`GET`/`POST /admin/mcp-tokens`, `DELETE /admin/mcp-tokens/{id}` ; le token en clair n'est renvoyé qu'à la création ; la création exige `current_password`) et reset database (exige `current_password`, écrit un instantané `data/backups/pre-reset_*.db` avant d'effacer).
- `notifications.py`: réglages des notifications push (`GET`/`PUT /notifications/settings`, jetons masqués `••••` + 4 derniers caractères ; un jeton renvoyé masqué n'écrase pas la valeur) et `POST /notifications/test` (`channel` = `ntfy|telegram`, 400 si incomplet, 502 si l'envoi échoue). Interdit aux tokens MCP (`require_interactive_session`). Envoi : `services/notifications.py (canaux : integrations/notifications.py)`.
- `health.py`: healthcheck public.

## Frontend

Routes dans `frontend/src/App.tsx`:

- `/login`: authentification.
- `/`: dashboard, 5 onglets : Aperçu (`OverviewTab`), Budgets, Dépenses (`MerchantsTab` + `SubscriptionsTab`), Analyse (`InsightsTab` + `HistoryTab`), Projections. Vue « Tous les comptes » par défaut, dernier compte choisi mémorisé (`localStorage`).
- `/accounts`: liste des comptes (incluant la bannière de validation périodique). `?import=1` ouvre l'import CSV (`components/import/ImportDialog`, sans compte présélectionné ; ⌘K et ancien `/settings?tab=import`).
- `/accounts/:id`: détail compte courant/épargne/investissement ; un compte `credit` affiche `components/loans/LoanView` (résumé, courbe du capital restant dû, tableau d'amortissement par année, simulateur de remboursement anticipé). `?new=tx&type=&amount=&merchant=` ouvre le formulaire de transaction pré-rempli, `state.openTransaction` ouvre une transaction en modification (⌘K). Bouton « Importer » : import CSV dans ce compte (`ImportDialog` → `ImportFlow`).
- `/accounts?new=loan` ouvre le formulaire « Ajouter un crédit » (`components/loans/LoanDialog`).
- `/savings`: objectifs d'épargne.
- `/tax`: Fiscalité (carte « Où placer ton prochain euro », plafonds PEA/PER/Livret A/LDDS/LEP/Livret Jeune, blocage 5 ans du PEE, dates clés PEA/AV, récap annuel CTO 2DC/3VG/3VH).
- `/investments`: vue globale investissements.
- `/month` (`MonthHub.tsx`, sous-routes) : `/month/bilan` (rapport mensuel, `MonthlyReport.tsx`), `/month/revue` (revue de fin de mois, `MonthReview.tsx`, `?year=&month=`), `/month/comparaison` (`Comparison.tsx`). Anciennes adresses `/report`, `/month-review`, `/comparison` redirigées avec leurs paramètres (`RedirectKeepingSearch`).
- `/recurring` « Échéances » : un seul des onglets `recurring` (Liste) ou `subscriptions` (Analyse Récurrences : Abonnements / Investissements / Autres récurrences dont le salaire, via `GET /analytics/subscriptions?include_other=true`) selon le sélecteur Analyse/Liste (localStorage `recurring-view`, défaut Analyse) ; puis `?tab=` calendar (`Calendar.tsx` en mode `embedded`) | salary (`SalaryManager`, salaire et télétravail). `/calendar` redirige vers `?tab=calendar`.
- `/audit`: Centre d'Actions (audit d'integrite, alertes budget, suggestions de regles) — voir `docs/ACTION_CENTER.md`. `?vue=virements` : revue des virements internes (`components/audit/TransferReview` : suggestions à lier/ignorer, virements liés à délier).
- `/classement` (groupe Gestion) : onglets `?tab=` categories | tags | merchants | rules (règles d'auto-catégorisation + règles de virement `TransferRulesSection`), composants dans `components/classement/`.
- `/tools` « Simulateur » : prévision simple (`WealthForecast`, « dans N ans » + « et si j'épargne +X ») avec bouton « Mode avancé » vers le simulateur complet (`WealthSimulator`).
- `/settings`: 4 onglets `?tab=` : general (profil, affichage : thème clair/sombre/auto propre à l'appareil, montants masqués à l'ouverture, positions simplifiées ; découpage des mois), notifications (ntfy/Telegram), security (mot de passe, passkey, TOTP, accès MCP, connexions récentes + « déconnecter tous les appareils »), data (sauvegarde avec son état, export CSV, historique des imports, réinitialisation). Les anciens onglets redirigent : account → security, system → data, categories/tags/merchants/rules → `/classement`, transferts → `/audit?vue=virements`, import → `/accounts?import=1`.

Principes:

- `AuthProvider` gere le token et l'etat de connexion.
- `ProtectedRoute` bloque les pages applicatives sans token.
- `UIProvider` porte l'etat UI global, dont le mode confidentialite.
- Omnibox (⌘K, `components/layout/Omnibox.tsx`) : navigation, comptes, recherche de transactions (ouverture directe en modification), actions (nouvelle transaction, import CSV, revue du mois, mode confidentialité, ajouter un crédit) et saisie rapide `lib/quickEntry.ts` (`12,50 boulangerie` = dépense, `+1200 prime` = revenu) qui ouvre le formulaire pré-rempli sur le compte principal, jamais d'enregistrement direct.
- `apiFetch()` centralise les appels JSON et redirige vers `/login` en cas de `401` (ou `403` hors `/auth/token`). `API_BASE` = `http://localhost:8001` sur localhost, `/api` ailleurs.
- Les uploads CSV n'utilisent pas `apiFetch()` pour laisser le navigateur definir le multipart boundary ; ils passent par `api.upload()` qui ajoute le Bearer sans `Content-Type`. Les exports utilisent `api.download()`.

## Modele De Donnees

### `accounts`

Champs principaux: `id`, `name`, `type`, `currency`, `created_at`, `active`, `color`, `asset_class`, `sector`, `geographic_zone`, `institution`, `logo` (réf. `si:<slug>` ou `file:<hash>.png`, même système que les récurrences), `fonds_euros_pct`, `fonds_investis_pct` (assurance-vie), `is_main`, `last_verified_at`, `tax_wrapper` (`pea`, `per`, `cto`, `assurance_vie`, `livret_a`, `livret_jeune`, `pee`, `ldds`, `lep`, nullable) et `opened_at` (date d'ouverture) pour la page Fiscalité. La suppression API est logique (`active=False`).

Types connus: `courant`, `epargne`, `investissement`, `assurance_vie` (`AccountType` dans `schemas/account.py`, imposé en création/modification), plus `credit`, créé et modifié uniquement via `/loans`. Un compte `credit` n'a pas de transactions : sa valeur est −capital restant dû (`services/wealth.py`), 0 avant le déblocage (un mois avant la première échéance), donc tous les totaux de patrimoine sont nets ; les filtres KPI `type in (courant, epargne)` l'excluent des revenus/dépenses.

### `categories`

Champs: `id`, `name`, `icon`, `color`, `type`, `monthly_limit`, `annual_limit`, `group`, `archived` (masquée des sélecteurs via `GET /categories?include_archived=false`, historique et analytics inchangés).

`name` est unique. Les limites alimentent les alertes budget.

### `transactions`

Champs: `id`, `account_id`, `date`, `month_label`, `type`, `merchant`, `merchant_id`, `category_id`, `amount`, `currency`, `original_amount`, `running_balance`, `note`, `is_recurring`, `recurring_transaction_id`, `is_subscription_ignored`, `custom_icon`, `custom_color`, `is_transfer`, `is_transfer_ignored`, `is_duplicate_ignored`, `linked_transaction_id`, `linked_investment_transaction_id`, `link_origin` (`manual` | `rule` | `recurring`), `transfer_rule_id`, `reimbursement_offset` (total remboursé pour une Sortie, total affecté pour une Entree ; maintenu par `services/reimbursements.py`). `is_exceptional` (dépense hors norme : reste dans les totaux et les soldes, isolée dans la lecture « hors exceptionnel » de la revue de mois). `splits` : parts de découpage (`transaction_splits`).

`amount` est le montant converti dans la devise du compte. `original_amount` et `currency` gardent la saisie d'origine. Les champs de liaison permettent de connecter des virements internes ou de rattacher une transaction à sa règle récurrente génératrice.

### `investment_transactions`

Champs: `id`, `account_id`, `date`, `type`, `amount`, `currency`, `original_amount`, `note`, `asset_class`, `sector`, `geographic_zone`, `ticker`, `isin`, `quantity`, `unit_price`, `price_currency`, `fees`, `etf_profile_id`, `is_transfer`, `is_transfer_ignored`, `linked_transaction_id`, `link_origin`, `transfer_rule_id`, `recurring_transaction_id`.

Types : `versement` / `retrait` (flux d'espèces, comptés dans le montant investi ; avec ticker + quantité ils font aussi bouger la position), `achat` / `vente` (opérations sur titres, ticker + quantité obligatoires, sans effet sur le montant investi), `dividende`, `frais`. `unit_price` et `fees` sont exprimés en `price_currency` (défaut : `currency`) ; sans `unit_price`, il est déduit du montant hors frais.

Valorisation (`core/portfolio.py`) : pour un compte `investissement` ayant des positions, **valeur = Σ quantité × dernier cours + espèces** ; les espèces partent du Point Zéro (relevé − inventaire valorisé, si un snapshot est à ±7 j) puis cumulent `versement` +, `retrait` −, `achat` −, `vente` +, `frais` −, `dividende` + (un versement/retrait portant un titre et une quantité est à la fois flux externe et opération : espèces inchangées). Montant investi **depuis l'origine du compte**, indépendant de la date du Point Zéro des positions = (snapshot Point Zéro s'il existe) + tous les versements − retraits datés après ; sans snapshot Point Zéro ni versement antérieur à l'inventaire, la valeur d'ouverture de l'inventaire compte comme investie. Les dividendes ne l'augmentent pas. La courbe reprend les snapshots antérieurs au Point Zéro des positions. Plus-value latente = valeur − coût de revient EUR (taux des achats), avec `fx_effect_eur` = part due au change ; plus-value réalisée rejouée par `core/holdings.py::replay_account` (produit net − coût EUR de la quantité vendue, par année). XIRR (flux datés, valeur actuelle en dernier) et TWR (chaîne entre les flux, sur la courbe reconstituée avec `security_prices` et taux datés). Les snapshots deviennent un contrôle : écart > 2 % sur le dernier relevé → action `reconciliation-gap-…`. L'assurance-vie, un compte sans position et un compte dont `accounts.valuation_mode = "snapshot"` (réglable sur la page du compte ; crypto par défaut : noms Coinbase/Ledger/… ou lignes uniquement en paires `XXX-EUR`) restent valorisés par snapshot (`value_source`). `/analytics/investments`, `/investments/{id}` et `/performance-history` utilisent cette valeur pour les comptes titres.

Dividendes (`core/dividends.py`) : `ticker` obligatoire à la création, `amount` = **net reçu** (comme chez le courtier), `withholding_tax` = retenue informative (même devise que `currency`, brut = net + retenue), `reinvested` = un `achat` lié (`reinvest_of_id`, non modifiable à la main) est généré avec `quantity` = parts reçues. Un dividende saisi marque la position comme distribuante (`portfolio_holdings.pays_dividends`, réglable à la main).

### `balance_snapshots`

Champs: `id`, `account_id`, `date`, `current_value`, `note`, `is_zero_point`.

Un point zéro sert de base de performance pour un compte.

### Autres Tables

- `portfolio_holdings`: positions titres par compte (`account_id`, `ticker`, `isin`, `asset_name`, `quantity`, `buy_price_avg` = PRU frais inclus dans `currency`, `cost_basis_eur` = coût aux taux historiques, `pays_dividends` = titre distribuant (rappel), `etf_profile_id`). **Dérivées** : recalculées par `core/holdings.py::rebuild_holdings` = inventaire `holding_baseline_items` + opérations sur titres postérieures à `accounts.holdings_baseline_date` (une opération sur titre antérieure est refusée en 422).
- `holding_baseline_items`: inventaire Point Zéro des positions (`account_id`, `baseline_date`, `ticker`, `quantity`, `buy_price_avg`, `currency`, …).
- `security_prices`: cours de clôture journaliers (`ticker`, `date`, `close`, `currency`, `source`), alimentés à chaque cotation Yahoo (`get_market_quotes(..., db=)`), par la tâche de fond horaire (`refresh_held_prices`) et par `get_price_on` / `fetch_price_history`. Si Yahoo échoue, le dernier cours stocké est renvoyé avec `stale=True`.
- `etf_profiles`: profils ETF (`name`, `ticker`, `isin`, `aliases`, `countries`, `sectors`, `top_holdings` en JSON texte, `is_system`, `composition_sources`, `composition_refreshed_at`). `composition_sources` donne la source de chaque champ : `yahoo` (réécrit à chaque actualisation), `preset` (préréglage des profils système dans `domain/etf_presets.json`, repli tant que Yahoo ne fournit pas le champ, réécrit au démarrage), `manual` (saisi via `PUT`, jamais écrasé). Le scanner de diversité compte la part non couverte d'un ETF en « Non renseigné » et renvoie l'origine des compositions dans `etf_compositions`.
- `system_settings`: paires cle/valeur (ex. `admin_username`, `admin_password_hash`, `mcp_enabled`, `ui.privacy_on_start`).
- `login_events`: tentatives de connexion (`created_at`, `method` = `password|password_totp|passkey`, `success`, `reason` = `invalid_password|invalid_totp|invalid_passkey|rate_limited`, `ip` (X-Real-IP de Nginx), `user_agent`). Écrites par `core/login_events.py::record_login` depuis `/auth/token`, `/auth/totp/login`, `/auth/passkey/login/verify` ; seules les 200 dernières sont gardées.
- `mcp_tokens`: tokens d'accès MCP (`name`, `token_hash` SHA-256 unique, `token_prefix` pour l'affichage, `created_at`, `last_used_at`).
- `imports_log`: journal d'import CSV.
- `historical_exchange_rates`: cache de taux historiques.
- `savings_goals`: objectifs d'épargne (`name`, `target_amount`, `keyword`, `deadline`, `account_id`, `category_id`, `icon`, `color`).
- `categorization_rules`: règles d'auto-catégorisation locale basées sur des patterns de commerçants (`id`, `pattern`, `category_id`, `transaction_type`, `merchant_name`, `priority`).
- `recurring_transactions`: définitions d'abonnements/charges fixes récurrentes (`id`, `account_id`, `name`, `type`, `amount`, `currency`, `category_id`, `frequency`, `day_of_month`, `start_date`, `end_date`, `excluded_months`, `last_generated_date`, `is_active`, `auto_generate`, `note`, `transfer_to_account_id`, `transfer_credit_day`, `asset_class`, `sector`, `geographic_zone`, `ticker`, `isin`, `quantity`, `unit_price`, `whole_shares`, `etf_profile_id`).
- `transfer_rules`: règles de virement interne (`source_account_id`, `dest_account_id`, `pattern` sur marchand/note de la sortie, `amount`, `amount_tolerance_pct`, `day_tolerance`, `is_active`). Moteur : `services/transfers.py`.
- `reimbursement_claims` (créance : `transaction_id` → Sortie, `debtor`, `expected_amount`, `note`) et `reimbursement_allocations` (`claim_id`, `entree_transaction_id`, `amount`, unique par couple). Moteur : `services/reimbursements.py` ; les KPI utilisent `NET_AMOUNT = amount − reimbursement_offset` (`repositories/analytics/common.py`).
- `month_closures` (revue de fin de mois : `year` + `month` uniques ensemble, `closed_at`, `highlight`, photo `tx_count` / `income` / `expenses` / `unresolved_count`, plus `fingerprint` : totaux entrées/sorties par devise de compte en JSON, sans conversion). Marqueur non bloquant ; « modifié depuis la clôture » = `tx_count` ou `fingerprint` différents du recalcul (comparaison exacte, insensible aux taux de change). Logique : `services/month_review.py`, route : `controllers/month_review.py`.
- `tags`: tags transversaux personnalisés (`id`, `name`, `color`, `archived`).
- `transaction_splits`: découpage d'une `Sortie` hors virement entre catégories (`transaction_id` CASCADE, `category_id`, `amount`, `note`) ; somme des parts = montant, aucune part Investissement/Epargne ni catégorie `revenu`, la transaction prend la catégorie de la plus grosse part. Logique : `services/splits.py`. Seules les répartitions par catégorie lisent les parts via `repositories/analytics/common.py::category_lines` (`expenses-by-category`, `budget-alerts`, `sankey`, `money-flow` variable, provisions, filtre `category_id` de `/transactions`) ; totaux, soldes et dépenses réelles inchangés. Changer type/montant d'une transaction découpée → 400 ; changer sa catégorie, la recatégoriser en masse ou la lier en virement annule le découpage.
- `loans`: paramètres d'un crédit (`account_id` unique CASCADE vers un compte `credit`, `kind` = `immobilier|auto|consommation|etudiant|autre`, `principal`, `annual_rate_pct`, `duration_months`, `start_date` = date de la 1re échéance, `insurance_monthly`). Mensualité constante hors assurance, échéance n à `start_date + (n−1) mois`, arrondi au centime par ligne, dernière ligne soldant le reste.
- `loan_prepayments`: remboursements anticipés effectués (`loan_id` CASCADE, `date`, `amount`, `mode` = `reduce_duration` garde la mensualité, `reduce_payment` la recalcule sur la durée restante), appliqués après la dernière échéance de date ≤ `date`.
- `financial_events`: journal des décisions (`date`, `title` ≤ 200, `note` ≤ 1000, `account_id` facultatif SET NULL). Note de contexte sans effet sur les calculs, affichée comme repère ⚑ (dans son mois civil) avec les faits marquants des clôtures sur la courbe « Flux de trésorerie » de l'onglet Historique du Dashboard, et gérée par la carte `components/dashboard/DecisionJournal`.
- `provisions`: grosses dépenses périodiques (`name`, `amount` EUR par échéance, `interval_months`, `due_date` = échéance de référence, `category_id` pour retrouver le paiement réel, `account_id` = compte de mise de côté, `note`, `active`). Purement prévisionnel, aucune transaction créée. Calcul `services/provisions.py` : prochaine/précédente échéance, `target_now` = montant × temps écoulé depuis l'échéance précédente, `monthly_needed` = (montant − constitué) ÷ mois restants ; constitution = solde du compte rattaché (`services/wealth.py::account_values`) réparti entre ses provisions au prorata de leur cible ; `behind` si constitué < cible − 1 € ; `last_payment` = plus grosse dépense de la catégorie à ±60 j de l'échéance précédente.
- `notification_log`: alertes déjà notifiées (`fingerprint` SHA-256 unique de `id|titre|description` de l'`ActionItem`, `action_id`, `channel` = canaux ayant reçu ou `init`, `sent_at`). Réglages dans `system_settings` (`notify.*` : canaux, sévérité minimale, résumé hebdo, masquage des montants, URL publique, `notify.initialized`, `notify.last_digest_week`).
- `transaction_tags`: table d'association many-to-many (`transaction_id`, `tag_id`).
- `merchants`: marchands canoniques (`id`, `name`, `category_id`, `icon`, `color`).
- `merchant_aliases`: alias et libellés bancaires d'origine associés aux marchands canoniques (`id`, `merchant_id`, `label`).
- `salary_configs`: configuration de salaire pour la génération TR/TT (`id`, `salary_account_id`, `ticket_account_id`, `net_salary`, `ticket_value`, `ticket_employee_share`, `salary_category_id`, `ticket_category_id`, `salary_recurring_id`, `ticket_recurring_id`, `is_active`).
- `salary_months`: statut de génération des salaires par mois (`id`, `salary_config_id`, `month_label`, `salary_date`, `ticket_date`, `is_generated`, `generated_at`).
- `telecommuting_days`: jours de télétravail déclarés par mois (`id`, `salary_config_id`, `date`, `month_label`).
- `dismissed_insights`: insights/anomalies de dépenses masqués par l'utilisateur (`id`, `title`, `dismissed_at`; `title` stocke l'`id` stable d'une insight/action masquee).

## Routes Principales

### Public

- `GET /health` → `{"status": "ok", "demo": bool}` (le frontend affiche les identifiants de démo et un bandeau quand `demo` est vrai)
- `POST /auth/token` (limite de tentatives par client/utilisateur)
- `GET /auth/whoami` (authentifié : JWT ou token MCP)

### CRUD Et Donnees

- `/accounts` (+ `POST /{id}/verify` ; `POST /{id}/reconcile` `{date, bank_balance}` : rapprochement avec le solde affiché par la banque, lecture seule. Compare au `running_balance` de fin de journée et liste des pistes (`duplicate` : même libellé, sens et montant à ≤ 3 j ; `extra_or_missing` : ligne dont le montant égale l'écart ; `wrong_sign` : ligne dont l'inversion comble l'écart ; `missing` en repli), recherchées sur les 60 jours précédant la date. Écart ≤ 0,01 → `last_verified_at` mis à jour. Logique : `services/reconciliation.py`. UI : bouton « Rapprocher » d'`AccountDetail` et « Saisir le solde » de la bannière de vérification, `components/accounts/ReconcileDialog`)
- `/categories`
- `/transactions`
- `/investment-transactions`
- `/balance-snapshots`
- `/goals`
- `/provisions` : `GET` (liste avec état calculé), `GET /summary` (total mensuel, échéances à 90 j, écart par compte rattaché), `POST`, `PATCH /{id}`, `DELETE /{id}`
- `/loans` : `GET` (résumés : mensualité courante, capital restant dû, % remboursé, date de fin, coût total), `POST` (crée le compte `credit` et le prêt), `GET|PATCH|DELETE /{id}` (la suppression retire aussi le compte), `GET /by-account/{account_id}`, `GET /{id}/schedule`, `POST /{id}/simulate-prepayment` (`amount`, `date`, `mode` ; rien n'est enregistré ; `max_penalty` = plafond légal min(6 mois d'intérêts, 3 % du CRD)), `POST /{id}/prepayments`, `DELETE /{id}/prepayments/{pp_id}`
- `/financial-events` : journal des décisions, `GET` (`start`, `end`, `account_id` facultatifs, plus récent d'abord), `POST`, `PATCH /{id}`, `DELETE /{id}`
- `/categorization-rules`
- `/recurring-transactions` (+ `POST /trigger`) ; `transfer_to_account_id` en fait une récurrence « virement » (sortie + entrée liées à chaque échéance) ; `transfer_credit_day` (1-31, optionnel) diffère l'arrivée : la sortie porte `transactions.transfer_credit_due` (premier jour `transfer_credit_day` à partir du débit) et l'entrée n'est créée qu'à cette date par la tâche de fond (jamais si la sortie a été liée ou déliée entre-temps) ; `whole_shares` (achat de titres sans quantité fixe) : quantité arrondie à l'entier inférieur et montant du versement = parts × cours (le reliquat reste chez le courtier, la sortie bancaire garde le montant prévu) ; `logo` optionnel (`si:<slug>` Simple Icons ou `file:<hash>.png` favicon local), repris par `TransactionRead.recurring_logo` et par les événements de `/analytics/calendar` (`logo`)
- `/logos` : `GET /search?q=` (catalogue Simple Icons embarqué `app/assets/simple_icons/`, CC0), `POST /from-domain` (télécharge une fois le favicon d'un domaine via le service favicon de Google, stocké dans `data/logos/`, réglage `logos_dir`) ; `GET /logos/img/{ref}` est **public** (lecture seule, référence validée par regex) car une balise `<img>` n'envoie pas le JWT
- `/transfer-rules` (CRUD, `PATCH /{id}` pour éditer une règle depuis Réglages › Virements, `POST /apply[?dry_run=true&rule_id=]` : rattrapage de l'historique)
- `/reimbursements` : `GET /claims?status=open|settled|all&debtor=`, `GET /summary`, `POST /claims`, `PATCH|DELETE /claims/{id}`, `GET /claims/{id}/candidates`, `POST /claims/{id}/allocations`, `DELETE /allocations/{id}`, `GET /entries/{entree_id}/claims`
- `/month-review` : `GET ?year=&month=` (étapes catégoriser, soldes, budget + statut de clôture + `modified_since_close`), `POST /close` (`year`, `month`, `highlight`, idempotent), `DELETE ?year=&month=` (rouvrir, 204), `GET /closures`
- `/transactions/potential-transfers[?months=&days_tolerance=&amount_tolerance_pct=]` (suggestions ; par défaut tout l'historique, ±5 j, ±1 %), `GET /transactions/{id}/transfer-candidates` (liaison manuelle), `POST /transactions/{id}/transfer-counterpart`, `link/{other_id}`, `unlink`, `ignore[?other_id=]`
- `/tags` (`GET ?include_archived=false` masque les archivés)
- `PUT /transactions/{id}/splits` (`{items:[{category_id, amount, note}]}`, liste vide = annuler) ; `GET /transactions` accepte aussi `uncategorized`, `merchant_name` (nom canonique exact), `period=true` (month/year = mois de paie) et `budget_scope=true` (courant/épargne hors tickets restaurant) : filtres du panneau de drill-down des graphiques
- `/merchants` (+ aliases, `auto-normalize`, `suggestions/unnormalized`)
- `/holdings`, `/etf-profiles`, `/market` (search, validate, quote)
- `/tax` (`GET /tax/overview`, `GET`/`PATCH /tax/settings`, `GET /tax/annual-report?year=`) : calculs dans `services/tax.py`, règles chiffrées par année dans `domain/tax_rules.py` (valeurs à vérifier), calculs purs dans `domain/tax.py` ; `overview.suggestions` = comptes actifs sans enveloppe dont le nom en évoque une (`domain/tax.py::guess_tax_wrapper`), proposés sur la page sans rien enregistrer d'office ; `overview.allocation_advice` = ordre de remplissage conseillé (`domain/tax.py::allocation_advice`, règle fixe : épargne de précaution < 6 mois de dépenses (`compute_resilience`) → premier livret avec de la place parmi LEP, Livret A, LDDS, Livret Jeune ; PEA avec de la place ou à ouvrir ; PER si TMI ≥ 30 % ; assurance-vie à ouvrir sinon CTO), `overview.precaution_months` ; plafonds LDDS 12 000 € et LEP 10 000 € (rappel de la condition de revenus, non vérifiée)
- `/salary` (config, months, telecommuting, summary, generate, work-time : taux horaire net pour le prix en heures de travail, réglages `work_days_per_year` / `work_hours_per_day` dans `system_settings`)
- `/admin` (profile, mcp-tokens, reset-database) — interdit aux tokens MCP

### Import Export

- `POST /import/preview`
- `POST /import/commit`
- `GET /export/transactions.csv`

### Analytics

- `GET /analytics/budget` (vue globale : `epargne_realisee` = revenus − dépenses réelles, numérateur du taux d'épargne ; `reste_tresorerie` = `epargne_realisee` − `investissements_du_mois` (versements liés inclus) ; `revenus_apres_depenses` reste revenus − `depenses_totales`)
- `GET /analytics/actions`, `POST /analytics/actions/dismiss`, `GET /analytics/audit`, `GET /analytics/audit/{issue_id}`
- `GET /analytics/cashflow-projection` (vue globale : ignore les récurrences de virement vers un compte déjà compté dans le solde et les récurrences « lapsed »), `GET /analytics/calendar`, `GET /analytics/patrimoine-allocation` (crédits hors items : `total_debts_eur`, `net_patrimoine_eur`)
- `GET /analytics/asset-allocation/suggestions`, `GET /analytics/diversity-scanner`
- `POST /analytics/insights/dismiss`, `POST /analytics/subscriptions/ignore`, `GET /analytics/tags`
- `GET /analytics/expenses-by-category`
- `GET /analytics/top-merchants`
- `GET /analytics/investments`
- `GET /holdings/estimate-costs?account_id=` : PRU estimé de chaque ligne du Point Zéro depuis les achats antérieurs à sa date (+ `coverage`) ; `POST /holdings/apply-costs` enregistre les PRU validés
- `GET /analytics/dividends` (`account_id`, `months`)
- `GET /analytics/portfolio` (vue globale EUR) et `GET /analytics/portfolio/{account_id}` : valeur calculée, espèces, montant investi, plus-value latente (+ effet de change par ligne), plus-value réalisée par année, dividendes, frais, XIRR, TWR, courbe reconstituée, rapprochement avec les snapshots
- `GET /analytics/investments/{account_id}`
- `GET /analytics/investments/{account_id}/performance-history`
- `GET /analytics/subscriptions` (`price_changes` : hausses de prix récentes, `services/subscription_prices.py`, série : `domain/subscription_prices.py` ; une série = sorties d'un même compte rattachées à la même récurrence, sinon au même marchand canonique, sinon au même libellé, d'échéance régulière (écart médian mensuel 25-35 j, trimestriel 80-100 j, annuel 340-390 j) et encore prélevée ; hausse = dernière suite de montants identiques supérieure d'au moins 0,10 et 1 % à la suite stable précédente (deux échéances, une pour l'annuel), signalée 6 mois (13 pour l'annuel) ; reprise au Centre d'Actions sous `subscription-price-{compte}-{clé}-{date}`) (`status` : `active`, `lapsed` = active mais aucune occurrence depuis plus de deux périodes + 7 j (`domain/finance.py::is_lapsed`, hors totaux), `paused`, `potential` ; `next_occurrence` cherchée sur 400 jours)
- `GET /analytics/wrapped?year=` (bilan annuel, `services/analytics/wrapped.py` (formules `domain/wrapped.py`) : agrège mois par mois `budget`, `expenses-by-category` (hors Investissement/Epargne) et `top-merchants` ; année en cours arrêtée au mois courant, `previous` = N-1 sur la même période, seulement si N-1 a des dépenses sur au moins la moitié des mois comparés ; variation de patrimoine hors soldes initiaux saisis dans l'année ; abonnements = récurrences `Sortie` hors virement et hors épargne/investissement, nouveaux = 1re échéance dans l'année, arrêtés = récurrence close (ou « lapsed » à la fin de la période) dont la dernière échéance tombe dans l'année ; heures de travail au taux horaire actuel)
- `GET /analytics/kpi-history` (mêmes règles que `budget` : virements internes exclus, seuls les versements liés à un virement comptent comme investis ; `taux_epargne` borné à ±100, `null` sans revenu ; `depenses` inclut les sorties catégorisées Investissement/Epargne, `depenses_reelles` non)
- `GET /analytics/budget-period[?year=&month=]` et `PUT` (`{"mode": "civil"|"salary"}`) : mois budgétaire en cours et fenêtre (`start`, `end` inclus) du mois demandé. Mois de paie (réglage `budget_month_mode`, défaut `salary`) : chaque salaire reçu (transaction `Entree` du compte salaire dont le libellé commence par « Salaire », ou de récurrence salaire, ou de catégorie « Salaire ») ouvre une période qui dure jusqu'au salaire suivant et porte le nom du mois qu'elle finance (salaire du 25 août → « septembre »). Logique unique dans `services/budget_period.py` (`period_bounds`, `period_key_expr`, `current_period` ; calcul des périodes dans `domain/budget_period.py`, dates de salaire dans `repositories/budget_period.py`) ; branchée sur `budget`, `budget-alerts`, `expenses-by-category`, `top-merchants`, `tags`, `kpi-history`, `timeseries`, `monthly-report`, `money-flow`, `sankey`, `insights`, `/month-review`. Sans salaire détecté : mois civil. Salaire manquant (écart > 45 j) : le trou entre deux périodes forme un mois « sans salaire » (`_fill_gaps`), aucun jour n'est hors période. Hors périmètre (restent en mois civil) : soldes, calendrier, cashflow-projection, investissements, fiscalité, `/wrapped` (forcé civil par `civil_months()`)
- `GET /analytics/resilience?month=&year=` (mois d'autonomie = épargne liquide ÷ dépenses réelles moyennes des 6 derniers mois complets ; aussi utilisé par le « fonds de sécurité » du score de santé)
- `GET /analytics/account-flow-summary` (flux net du mois, variation, dépense moyenne d'un compte ; virements exclus)
- `GET /analytics/investments-allocation`
- `GET /analytics/investments-allocation-advanced`
- `GET /analytics/timeseries`
- `GET /analytics/budget-alerts`
- `GET /analytics/insights`
- `GET /analytics/wealth-simulation` (mode avancé : Monte Carlo, événements, fiscalité)
- `GET /analytics/wealth-forecast` (prévision simple : patrimoine total + épargne moyenne 12 mois (hors mois de tête sans dépense, avant le début du suivi), XIRR constaté (`/analytics/portfolio`) appliqué aux seuls comptes valorisés par positions sur lesquels il est mesuré (`investissement`), comptes d'investissement suivis par relevé à 0 % (`investissement_non_mesure`) sauf `investment_return_pct` qui s'applique à tous, autres comptes 0 %, aucun taux codé en dur, `years`, `extra_monthly`, surcharges `monthly_savings` / `investment_return_pct` / `savings_return_pct` ; la réponse détaille les mois et soldes par type utilisés)
- `GET /analytics/fire` (indépendance financière : cible = dépenses annuelles ÷ `withdrawal_rate_pct` (4 par défaut), dépenses réelles moyennes et épargne des mois de `wealth-forecast`, rendement nominal de `wealth-forecast` moins `inflation_pct` (2 par défaut) → projection en euros constants, `years_to_fi` (`null` au-delà de 80 ans), scénarios +100/+250/+500 €/mois et dépenses −10 % ; surcharges `return_pct`, `monthly_savings`, `annual_expenses`)
- `GET /analytics/sankey` (les nœuds de catégorie de dépense portent `category_id`, cliquables vers le panneau de drill-down ; nœud Budget équilibré : Investissements = `investissements_du_mois`, Épargne = entrées − dépenses catégorisées − investissements, Déficit sinon)
- `GET /analytics/money-flow` (vue globale : `investments` inclut les versements liés à un virement interne, comme `investissements_du_mois`)
- `GET /analytics/monthly-report` (`net_worth_change` hors soldes initiaux saisis dans le mois ; inclut `exceptional_expenses`, `real_expenses_excl_exceptional`, `savings_excl_exceptional`, `savings_rate_excl_exceptional`, `burn_rate_excl_exceptional`; `top_categories` : 8 premières catégories avec `prev_total`, total du mois précédent)

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
