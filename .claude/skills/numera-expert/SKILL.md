---
name: numera-expert
description: Connaissance métier de Numera (budget + investissements) : règles de calcul, virements internes, point zéro, salaire/télétravail, marchands, Centre d'Actions, import CSV. À charger avant de toucher à une logique financière, un KPI, un import ou une règle d'audit.
---

# Numera — logique métier

Les règles critiques courtes sont dans le `CLAUDE.md` racine ; ce skill détaille les mécanismes qui demandent de lire plusieurs fichiers.

## Soldes et types de transactions

- `transactions.amount > 0` toujours ; `type` ∈ `Entree | Sortie | Interets | Solde Initial`. Impact sur le solde : `core/finance.py::apply_transaction_to_balance` (`Solde Initial` remplace le solde, il n'est ni revenu ni dépense).
- `running_balance` est stocké et recalculé en entier par `api/transactions.py::recalculate_running_balances(db, account_id)` après toute mutation, bulk, liaison/déliaison de virement et import.
- Investissement : `investment_transactions` (`versement | retrait` = flux d'espèces comptés dans le montant investi ; `achat | vente` = opérations sur titres ; `dividende` ; `frais`), `balance_snapshots` pour la valeur saisie ; `portfolio_holdings` pour les positions (ticker, ISIN, quantité, PRU frais inclus, `cost_basis_eur`) reliées à un `etf_profile`.
- Positions dérivées : inventaire Point Zéro (`holding_baseline_items`, daté par `accounts.holdings_baseline_date`) + opérations sur titres postérieures, recalculées par `core/holdings.py::rebuild_holdings`. Une opération sur titre antérieure au Point Zéro est refusée ; pour corriger un PRU ou une quantité de départ, on modifie la ligne d'inventaire (`PUT /holdings/{id}`).
- Dividendes : `type = dividende` avec ticker obligatoire ; `amount` = net reçu, `withholding_tax` informatif, `reinvested` crée un `achat` lié (`reinvest_of_id`). Saisie **manuelle** (le montant du courtier fait foi, pas de détection Yahoo). Agrégats EUR : `core/dividends.py`, `GET /analytics/dividends`. Les dividendes ne comptent pas dans le montant investi.
- PRU manquant sur une ligne du Point Zéro : `core/holdings.py::estimate_baseline_costs` le déduit des achats antérieurs à l'inventaire (bouton « Estimer les PRU », validation manuelle).
- Valeur d'un compte titres (PEA/CTO/crypto) = positions × cours + espèces (`core/portfolio.py`, `GET /analytics/portfolio[/{id}]`) ; assurance-vie et comptes sans position = dernier snapshot. Les snapshots servent au rapprochement (écart > 2 % → Centre d'Actions). Plus-value latente avec effet de change, plus-value réalisée par année (base de la 2074), XIRR et TWR sont calculés côté backend.
- Cours : stockés dans `security_prices` (une clôture par ticker et par jour), le dernier cours connu sert de repli (`stale`) si Yahoo ne répond pas.

## Virements internes

Détection : `GET /transactions/potential-transfers` ; liaison : `POST /transactions/{id}/link/{other_id}` (`is_transfer`, `linked_transaction_id`), `.../unlink`, `.../ignore` (`is_transfer_ignored`). Un virement vers un compte `investissement` peut pointer vers une `investment_transaction`. Les « dépenses réelles » et le taux d'épargne excluent ces transferts (voir `api/analytics/metrics.py`, `budget.py`).

## Point zéro et performance

Un seul `is_zero_point` par compte investissement (`POST /balance-snapshots/set-zero-point`). Performance : compte titres = valeur calculée (positions × cours + espèces, `core/portfolio.py`) − montant investi ; assurance-vie = dernier snapshot − base point zéro − flux (`api/analytics/investments.py`). Allocation avancée et scanner de diversification utilisent les `etf_profiles` (pays/secteurs/top holdings en JSON texte).

## Marchands et catégorisation

- `merchant` = libellé bancaire brut, jamais modifié. `merchant_id` → `merchants` canoniques via `merchant_aliases` (`POST /merchants/auto-normalize`, `GET /merchants/suggestions/unnormalized`).
- `categorization_rules` : `pattern` insensible à la casse sur marchand/note, `priority` décroissante, `POST /categorization-rules/apply-all`. L'import applique aussi les règles.

## Récurrences, abonnements, salaire

- `recurring_transactions` : `frequency` (monthly/weekly/quarterly/yearly), `excluded_months`, `auto_generate`. Génération par `core/recurring.py` (tâche de fond horaire + `POST /recurring-transactions/trigger`). Peut aussi porter des lignes d'achat de titres (ticker, quantité, prix).
- Abonnements détectés dynamiquement (`/analytics/subscriptions`), ignorables (`is_subscription_ignored`).
- Salaire : `salary_configs` (comptes salaire/tickets, net, valeur ticket, part salarié), `telecommuting_days` (jours TT), `salary_months` (`is_generated`). `POST/DELETE /salary/generate/{year}/{month}` crée / supprime la transaction. `core/salary.py` génère **une seule** transaction « Salaire » = `net_salary − nb_jours_TT × ticket_employee_share` (pas de transaction TR : les tickets sont informatifs) ; idempotent.

## Import / export CSV

Colonnes obligatoires : `Date, Mois, Type, Commercant, Categorie, Montant` (aliases d'en-têtes dans `HEADER_ALIASES`). `POST /import/preview` (aucune écriture) puis `POST /import/commit` ; idempotent sur `(account_id, date, amount, merchant, type)` ; `imports_log` ; recalcul final des soldes. Export : `GET /export/transactions.csv` (format Numbers).

## Centre d'Actions (`/analytics/actions`, page `Audit.tsx`)

Agrège : audit d'intégrité (`/analytics/audit`, issues avec `id` stable : `uncategorized-expenses`, `missing-merchants`, `unnormalized-merchants`, `duplicate-transactions`, `missing-initial-balances`, `stale-investment-snapshots`, `unused-categories`, `unmatched-transfers`), alertes budget (`/analytics/budget-alerts`) et suggestions de règles. `ActionItem.action_type` pilote la modale côté frontend (`link`, `modal_categorize`, `modal_rule`, `modal_snapshot`, `modal_merchant`). Les éléments écartés sont persistés (`POST /analytics/actions/dismiss`, `dismissed_insights`). Ajouter une action : voir `docs/ACTION_CENTER.md`.

## Vérification de compte

`accounts.last_verified_at` est mis à jour uniquement par `POST /accounts/{id}/verify` (bouton de `AccountVerificationBanner`).

## Services externes

Frankfurter (taux), Yahoo Finance (recherche/cotations titres, profils ETF). Aucun autre appel sortant, pas de télémétrie.

## Référence

`ARCHITECTURE.md` (modèle de données et routes), `backend/CLAUDE.md`, `frontend/src/CLAUDE.md`, skills `numera-backend`, `numera-frontend`, `numera-testing`.
