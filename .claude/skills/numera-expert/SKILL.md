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
- PRU manquant sur une ligne du Point Zéro : `core/holdings.py::estimate_baseline_costs` le déduit des achats antérieurs à l'inventaire (prix × quantité, ou, pour les anciens versements sans titre ni quantité, montant versé rattaché par libellé ÷ parts détenues) (bouton « Estimer les PRU », validation manuelle).
- Valeur d'un compte titres (PEA/CTO/crypto) = positions × cours + espèces (`core/portfolio.py`, `GET /analytics/portfolio[/{id}]`) ; assurance-vie et comptes sans position = dernier snapshot. Les snapshots servent au rapprochement (écart > 2 % → Centre d'Actions). Plus-value latente avec effet de change, plus-value réalisée par année (base de la 2074), XIRR et TWR sont calculés côté backend.
- Cours : stockés dans `security_prices` (une clôture par ticker et par jour), le dernier cours connu sert de repli (`stale`) si Yahoo ne répond pas.

## Virements internes

Un virement est un couple **1 pour 1** : une `Sortie` et une `Entree` (ou un `versement` d'investissement) sur deux comptes différents (`is_transfer`, `linked_transaction_id` / `linked_investment_transaction_id`). Un lien ne change aucun montant. Les « dépenses réelles », les revenus et le taux d'épargne excluent ces lignes (`api/analytics/metrics.py`, `budget.py`). Toute la logique est dans `core/transfers.py` :

- `link_pair` / `unlink_pair` : seule porte d'entrée pour lier ou délier (endpoints `POST /transactions/{id}/link/{other_id}`, `.../unlink`). `link_origin` = `manual` | `rule` | `recurring` ; `transfer_rule_id` = règle à l'origine.
- **Délier un lien `rule` ou `recurring`** marque les deux lignes `is_transfer_ignored`, sinon la règle les relierait aussitôt. Un lien manuel délié n'est pas ignoré.
- `find_pairs` : appariement 1 pour 1 global (écart de date, puis de montant), une entrée n'est jamais utilisée pour deux sorties ; les égalités parfaites sont renvoyées `ambiguous=True` et jamais liées seules. Sert aux suggestions (`GET /transactions/potential-transfers?months=`, 24 mois par défaut, 0 = tout) et aux règles.
- `transfer_rules` (`/transfer-rules`) : compte source → compte destination, `pattern` optionnel (marchand/note de la sortie), `amount` optionnel, tolérances (1 % / 5 jours par défaut). `apply_rules` lie les couples sans ambiguïté ; déclenché après un import CSV, la création/modification d'une transaction et la génération des récurrences (fenêtre de 3 mois, `auto_link_transfers` n'échoue jamais), et sur tout l'historique par `POST /transfer-rules/apply` (`dry_run=true` pour l'aperçu).
- Récurrence « virement » : `recurring_transactions.transfer_to_account_id` (Sortie d'un compte non titres) → chaque échéance crée la sortie **et** l'entrée/le versement (`create_counterpart`, conversion de devise, soldes recalculés), liées avec `link_origin = recurring`. Avec un ticker (destination `investissement` uniquement), la jambe d'entrée est un `versement` avec titre : dépôt **et** achat de parts en une opération (cash neutre, compté une seule fois dans le montant investi), `rebuild_holdings` relancé. Deux récurrences existantes (une par compte) sont reliées par une règle.
- Liaison manuelle : `GET /transactions/{id}/transfer-candidates` (±15 j, ±5 %, tous comptes) et `POST /transactions/{id}/transfer-counterpart` (crée l'entrée manquante). UI : `TransferLinkDialog` (bouton sur chaque ligne d'`AccountDetail`) et onglet Paramètres › Virements.

## Point zéro et performance

Un seul `is_zero_point` par compte investissement (`POST /balance-snapshots/set-zero-point`). Performance : compte titres = valeur calculée (positions × cours + espèces, `core/portfolio.py`) − montant investi ; assurance-vie = dernier snapshot − base point zéro − flux (`api/analytics/investments.py`). Allocation avancée et scanner de diversification utilisent les `etf_profiles` (pays/secteurs/top holdings en JSON texte).

## Marchands et catégorisation

- `merchant` = libellé bancaire brut, jamais modifié. `merchant_id` → `merchants` canoniques via `merchant_aliases` (`POST /merchants/auto-normalize`, `GET /merchants/suggestions/unnormalized`).
- `categorization_rules` : `pattern` insensible à la casse sur marchand/note, `priority` décroissante, `POST /categorization-rules/apply-all`. L'import applique aussi les règles.

## Récurrences, abonnements, salaire

- `recurring_transactions` : `frequency` (monthly/weekly/quarterly/yearly), `excluded_months`, `auto_generate`. Génération par `core/recurring.py` (tâche de fond horaire + `POST /recurring-transactions/trigger`). Peut aussi porter des lignes d'achat de titres (ticker, quantité, prix). Quantité ou prix non fixés : le prix est la **clôture du jour de l'échéance** (`market_data.get_price_on`, y compris pour les échéances rattrapées), repli sur la cotation en direct, quantité = montant ÷ prix (`core/recurring.py::_size_trade`).
- Abonnements détectés dynamiquement (`/analytics/subscriptions`), ignorables (`is_subscription_ignored`).
- Salaire : `salary_configs` (comptes salaire/tickets, net, valeur ticket, part salarié), `telecommuting_days` (jours TT), `salary_months` (`is_generated`). `POST/DELETE /salary/generate/{year}/{month}` crée / supprime la transaction. `core/salary.py` génère **une seule** transaction « Salaire » = `net_salary − nb_jours_TT × ticket_employee_share` (pas de transaction TR : les tickets sont informatifs) ; idempotent.

## Import / export CSV

Colonnes obligatoires : `Date, Mois, Type, Commercant, Categorie, Montant` (aliases d'en-têtes dans `HEADER_ALIASES`). `POST /import/preview` (aucune écriture) puis `POST /import/commit` ; idempotent sur `(account_id, date, amount, merchant, type)` ; `imports_log` ; recalcul final des soldes. Export : `GET /export/transactions.csv` (format Numbers).

## Centre d'Actions (`/analytics/actions`, page `Audit.tsx`)

Agrège : audit d'intégrité (`/analytics/audit`, issues avec `id` stable : `uncategorized-expenses`, `missing-merchants`, `unnormalized-merchants`, `duplicate-transactions`, `missing-initial-balances`, `stale-investment-snapshots`, `unused-categories`, `unmatched-transfers`), alertes budget (`/analytics/budget-alerts`) et suggestions de règles. `ActionItem.action_type` pilote la modale côté frontend (`link`, `modal_categorize`, `modal_rule`, `modal_snapshot`, `modal_merchant`). Les éléments écartés sont persistés (`POST /analytics/actions/dismiss`, `dismissed_insights`). Ajouter une action : voir `docs/ACTION_CENTER.md`.

## Vérification de compte

`accounts.last_verified_at` est mis à jour uniquement par `POST /accounts/{id}/verify` (bouton de `AccountVerificationBanner`).

## Fiscalité et enveloppes (`/tax`, page `Tax.tsx`)

`accounts.tax_wrapper` (`pea`, `per`, `cto`, `assurance_vie`, `livret_a`) et `opened_at` activent le suivi. Règles dans `core/tax.py`, valeurs chiffrées uniquement dans `core/tax_rules.py` (table par année, à vérifier chaque année) :

- **PEA** : versements cumulés (somme des `versement`) face à 150 k€ ; un retrait ne restitue pas de place ; retrait avant 5 ans = alerte ; alerte si le compte démarre d'un inventaire / Point Zéro (versements antérieurs non saisis, place restante surestimée).
- **PER** : versements de l'année civile **de tous les PER actifs additionnés** (plafond du foyer, une seule carte) face au plafond de déduction = 10 % des revenus pro N-1 borné entre plancher et maximum ; économie d'impôt = versé déductible × TMI.
- **Livret A** : solde actuel du compte face au plafond (alerte « plafond atteint » : les intérêts capitalisés peuvent légitimement le dépasser).
- **Livret Jeune** : idem face à 1 600 € ; l'âge (12-25 ans) n'est pas contrôlé.
- **PEE** (`pee`) : chaque `versement` est indisponible 5 ans (les `retrait` s'imputent sur les plus anciens) → total versé, bloqué, disponible, prochain déblocage ; plafond des versements volontaires de l'année = 25 % du salaire brut annuel (réglage `tax_gross_annual_salary`). Un versement dont la note contient « abondement » est l'abondement de l'employeur : il compte dans le total et le blocage, jamais dans le plafond. Aucun impôt calculé (taux de prélèvements sociaux du PEE non confirmé).
- **Assurance-vie** : ancienneté face à 8 ans et abattement annuel rappelé (seul / couple) ; la part de gain d'un rachat n'est pas calculée.
- **CTO** : seul compte concerné par le récap annuel : dividendes bruts (net + retenue, case 2DC), plus-values réalisées (3VG) ou moins-values (3VH) issues du rejeu `replay_account` (aucun appel réseau), impôt estimé au PFU par catégorie (`pfu_rate_dividends` et `pfu_rate_gains`, car la hausse de la CSG à 10,6 % s'applique dès les revenus 2025 aux plus-values mais seulement à partir du 1.1.2026 aux dividendes : en 2025, 30 % sur les dividendes et 31,4 % sur les plus-values ; 31,4 % partout en 2026 ; l'assurance-vie reste à 17,2 %) ; une perte ne compense pas les dividendes. Ventes sans coût de revient connu : signalées, jamais comptées à zéro en silence.
- Réglages (`system_settings`) : `tax_tmi_pct`, `tax_prior_year_pro_income`, `tax_household`, `tax_gross_annual_salary`.

## Services externes

Frankfurter (taux), Yahoo Finance (recherche/cotations titres, profils ETF). Aucun autre appel sortant, pas de télémétrie.

## Référence

`ARCHITECTURE.md` (modèle de données et routes), `backend/CLAUDE.md`, `frontend/src/CLAUDE.md`, skills `numera-backend`, `numera-frontend`, `numera-testing`.
