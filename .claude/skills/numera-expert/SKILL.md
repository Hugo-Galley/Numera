---
name: numera-expert
description: Connaissance métier de Numera (budget + investissements) : règles de calcul, virements internes, point zéro, salaire/télétravail, marchands, Centre d'Actions, import CSV. À charger avant de toucher à une logique financière, un KPI, un import ou une règle d'audit.
---

# Numera — logique métier

Les règles critiques courtes sont dans le `CLAUDE.md` racine ; ce skill détaille les mécanismes qui demandent de lire plusieurs fichiers.

## Soldes et types de transactions

- `transactions.amount > 0` toujours ; `type` ∈ `Entree | Sortie | Interets | Solde Initial`. Impact sur le solde : `domain/finance.py::apply_transaction_to_balance` (`Solde Initial` remplace le solde, il n'est ni revenu ni dépense).
- `running_balance` est stocké et recalculé en entier par `services/balances.py::recalculate_running_balances(db, account_id)` après toute mutation, bulk, liaison/déliaison de virement et import.
- Investissement : `investment_transactions` (`versement | retrait` = flux d'espèces comptés dans le montant investi ; `achat | vente` = opérations sur titres ; `dividende` ; `frais`), `balance_snapshots` pour la valeur saisie ; `portfolio_holdings` pour les positions (ticker, ISIN, quantité, PRU frais inclus, `cost_basis_eur`) reliées à un `etf_profile`.
- Positions dérivées : inventaire Point Zéro (`holding_baseline_items`, daté par `accounts.holdings_baseline_date`) + opérations sur titres postérieures, recalculées par `services/holdings/rebuild.py::rebuild_holdings`. Une opération sur titre antérieure au Point Zéro est refusée ; pour corriger un PRU ou une quantité de départ, on modifie la ligne d'inventaire (`PUT /holdings/{id}`).
- Dividendes : `type = dividende` avec ticker obligatoire ; `amount` = net reçu, `withholding_tax` informatif, `reinvested` crée un `achat` lié (`reinvest_of_id`). Saisie **manuelle** (le montant du courtier fait foi, pas de détection Yahoo). Agrégats EUR : `services/dividends.py` + `domain/dividends.py`, `GET /analytics/dividends`. Les dividendes ne comptent pas dans le montant investi.
- PRU manquant sur une ligne du Point Zéro : `services/holdings/cost_estimates.py::estimate_baseline_costs` le déduit des achats antérieurs à l'inventaire (prix × quantité, ou, pour les anciens versements sans titre ni quantité, montant versé rattaché par libellé ÷ parts détenues) (bouton « Estimer les PRU », validation manuelle).
- Valeur d'un compte titres (PEA/CTO/crypto) = positions × cours + espèces (`services/portfolio/`, `GET /analytics/portfolio[/{id}]`) ; assurance-vie et comptes sans position = dernier snapshot. **Source unique** pour la valeur courante : `services/portfolio/compute.py::positions_values_eur`, utilisée par `patrimoine-allocation`, `budget` (période en cours, assurances-vie incluses dans `patrimoine_net_total`) et `investments-allocation` ; les mois passés gardent le dernier relevé daté. Les snapshots servent au rapprochement (écart > 2 % → Centre d'Actions). Plus-value latente avec effet de change, plus-value réalisée par année (base de la 2074), XIRR et TWR sont calculés côté backend.
- Cours : stockés dans `security_prices` (une clôture par ticker et par jour), le dernier cours connu sert de repli (`stale`) si Yahoo ne répond pas.

## Revenu et patrimoine (définitions uniques)

- **Revenu** : `income_criterion(db)` (`repositories/analytics/common.py`, requête jointe à `Account`) = entrée sur un compte `courant`, ou entrée dont la catégorie est de type `revenu` (marquage explicite d'un revenu arrivé ailleurs), ou `Interets`. `Solde Initial` et virements internes jamais. Le money-flow reprend le `revenus_totaux` du budget ; le Sankey, le timeseries et `kpi-history` appliquent le même critère. Un dépôt non lié sur un livret n'est donc pas un revenu.
- **Périmètre des flux** (revenus/dépenses, répartition par catégorie, top marchands, Sankey) : comptes `courant` et `epargne` hors tickets restaurant ; `expenses-by-category` ajoute un bloc « Sans catégorie » pour que son total égale `depenses_totales`.
- **Patrimoine** : `services/wealth.py::account_values(db, accounts, at=None)` → valeur par compte (positions × cours pour un compte titres valorisé ainsi ; sinon relevé ; pour courant/épargne/autres le plus récent entre relevé et dernier solde ; rien = 0). Utilisé par `patrimoine-allocation`, `investments-allocation(-advanced)` et `budget.patrimoine_net_total` (tous les comptes actifs, y compris l'ancien type `bank`).
- **Crédits** : un compte `credit` (créé via `/loans`, jamais via `/accounts`) vaut −capital restant dû de son prêt (`domain/loans.py` (`loan_remaining` : `services/loans.py`)) : tous les totaux de patrimoine sont donc **nets**. `patrimoine-allocation` sort les crédits du camembert (`total_debts_eur`, `net_patrimoine_eur`). Pas de transactions sur un compte crédit : les mensualités restent des `Sortie` du courant (dépenses normales).
- **Mois de paie** : `build_periods` comble les trous (mois sans salaire = fenêtre propre, second salaire d'un même mois absorbé) pour que chaque jour appartienne à une période.

## Virements internes

Un virement est un couple **1 pour 1** : une `Sortie` et une `Entree` (ou un `versement` d'investissement) sur deux comptes différents (`is_transfer`, `linked_transaction_id` / `linked_investment_transaction_id`). Un lien ne change aucun montant. Les « dépenses réelles », les revenus et le taux d'épargne excluent ces lignes (`services/analytics/metrics/`, `services/analytics/budget/`). Toute la logique est dans `services/transfers.py` :

- `link_pair` / `unlink_pair` : seule porte d'entrée pour lier ou délier (endpoints `POST /transactions/{id}/link/{other_id}`, `.../unlink`). `link_origin` = `manual` | `rule` | `recurring` ; `transfer_rule_id` = règle à l'origine.
- **Délier un lien `rule` ou `recurring`** marque les deux lignes `is_transfer_ignored`, sinon la règle les relierait aussitôt. Un lien manuel délié n'est pas ignoré.
- `find_pairs` : appariement 1 pour 1 global (écart de date, puis de montant), une entrée n'est jamais utilisée pour deux sorties ; les égalités parfaites sont renvoyées `ambiguous=True` et jamais liées seules. Sert aux suggestions (`GET /transactions/potential-transfers?months=`, tout l'historique par défaut, ±5 j et ±1 % réglables depuis l'onglet Virements) et aux règles.
- `transfer_rules` (`/transfer-rules`) : compte source → compte destination, `pattern` optionnel (marchand/note de la sortie), `amount` optionnel, tolérances (1 % / 5 jours par défaut). `apply_rules` lie les couples sans ambiguïté ; déclenché après un import CSV, la création/modification d'une transaction et la génération des récurrences (fenêtre de 3 mois, `auto_link_transfers` n'échoue jamais), et sur tout l'historique par `POST /transfer-rules/apply` (`dry_run=true` pour l'aperçu).
- Récurrence « virement » : `recurring_transactions.transfer_to_account_id` (Sortie d'un compte non titres) → chaque échéance crée la sortie **et** l'entrée/le versement (`create_counterpart`, conversion de devise, soldes recalculés), liées avec `link_origin = recurring`. Avec un ticker (destination `investissement` uniquement), la jambe d'entrée est un `versement` avec titre : dépôt **et** achat de parts en une opération (cash neutre, compté une seule fois dans le montant investi), `rebuild_holdings` relancé. Deux récurrences existantes (une par compte) sont reliées par une règle. Arrivée différée (`transfer_credit_day`, ex. débit le 29, PEA crédité le 16) : la sortie reste en transit (`transactions.transfer_credit_due`), l'entrée/le versement (et l'achat au cours de ce jour) est créé par `_credit_pending_transfers` une fois la date passée ; échéance levée sans crédit si la sortie a été liée ou déliée entre-temps.
- Liaison manuelle : `GET /transactions/{id}/transfer-candidates` (±15 j, ±5 %, tous comptes) et `POST /transactions/{id}/transfer-counterpart` (crée l'entrée manquante). UI : `TransferLinkDialog` (bouton sur chaque ligne d'`AccountDetail`) règles dans Gestion › Classement › Règles, suggestions et virements liés dans Centre d'actions › Virements internes (`/audit?vue=virements`).

## Découpage, provisions, archivage

- **Découpage** (`services/splits.py`, `PUT /transactions/{id}/splits`) : une `Sortie` hors virement répartie en parts dont la somme égale le montant ; jamais de part Investissement/Epargne ni `revenu` (sinon les dépenses réelles changeraient). La transaction prend la catégorie de la plus grosse part. Toute répartition **par catégorie** passe par `repositories/analytics/common.py::category_lines()` (une ligne par part, remboursement au prorata) au lieu de `Transaction.category_id` ; les totaux n'en dépendent pas.
- **Provisions** (`services/provisions.py`, `/provisions`) : prévisionnel pur (aucune transaction). Effort mensuel = (montant − constitué) ÷ mois restants ; constitué = solde du compte rattaché réparti au prorata des cibles, sinon théorique.
- **Archivage** : `categories.archived`, `tags.archived` (masqués des sélecteurs avec `?include_archived=false`, rien ne change dans l'historique ni les analytics) ; un compte archivé = `accounts.active = False` (`DELETE /accounts/{id}`, réactivation par `PATCH active=true`).

## Remboursements

Une `Sortie` porte des **créances** (`reimbursement_claims` : débiteur libre, montant attendu) ; des `Entree` leur sont **affectées** avec un montant (`reimbursement_allocations`, plusieurs entrées par créance et plusieurs créances par entrée). Tout passe par `services/reimbursements.py`, qui recalcule `transactions.reimbursement_offset` (Sortie : total reçu ; Entree : total affecté).

- KPI revenus/dépenses **nets** sur le mois et la catégorie de la dépense : `NET_AMOUNT = amount − reimbursement_offset` (`repositories/analytics/common.py`) dans budget, budget-alerts, expenses-by-category, top-merchants, tags, kpi-history, timeseries, monthly-report, money-flow, sankey, insights. Restent **bruts** : soldes, account-flow-summary, calendar, cashflow-projection, subscriptions, tax, série salaire.
- Règles : Sortie ↔ Entree, même devise de compte, jamais un virement interne (et `find_pairs` / `candidates_for` / la liaison manuelle excluent ces transactions), plafonds (créances ≤ dépense, affectations ≤ attendu et ≤ entrée, arrondi au centime), attendu jamais sous le reçu. Modifier le type ou baisser le montant d'une transaction liée est refusé (400) ; supprimer l'une libère l'autre (`detach_before_delete` + `sync_offsets`).
- Abandon : ramener l'attendu au reçu, ou supprimer la créance. Pas d'espèces, pas de liaison automatique (candidates : débiteur dans le libellé, puis montant exact, puis date ; −7 j / +180 j).
- Centre d'Actions : `unallocated-reimbursements` (entrées « Remboursement… » des 180 derniers jours non affectées, s'il existe une créance ouverte).

## Point zéro et performance

Un seul `is_zero_point` par compte investissement (`POST /balance-snapshots/set-zero-point`). Performance : compte titres = valeur calculée (positions × cours + espèces, `services/portfolio/`) − montant investi ; assurance-vie = dernier snapshot − base point zéro − flux (`services/analytics/investments/flows.py`). Allocation avancée et scanner de diversification utilisent les `etf_profiles` (pays/secteurs/top holdings en JSON texte). Secteurs et top 10 viennent de Yahoo (actualisation hebdomadaire) ; les pays ne sont jamais fournis par Yahoo (préréglage des profils système ou saisie). Aucune composition n'est devinée : un champ inconnu reste vide et sa part est comptée en « Non renseigné ».

## Marchands et catégorisation

- `merchant` = libellé bancaire brut, jamais modifié. `merchant_id` → `merchants` canoniques via `merchant_aliases` (`POST /merchants/auto-normalize`, `GET /merchants/suggestions/unnormalized`).
- `categorization_rules` : `pattern` insensible à la casse sur marchand/note, `priority` décroissante, `POST /categorization-rules/apply-all`. L'import applique aussi les règles.

## Récurrences, abonnements, salaire

- `recurring_transactions` : `frequency` (monthly/weekly/quarterly/yearly), `excluded_months`, `auto_generate`. Génération par `services/recurring.py` (tâche de fond horaire + `POST /recurring-transactions/trigger`). Peut aussi porter des lignes d'achat de titres (ticker, quantité, prix). Quantité ou prix non fixés : le prix est la **clôture du jour de l'échéance** (`services/market/quotes.py::get_price_on`, y compris pour les échéances rattrapées), repli sur la cotation en direct, quantité = montant ÷ prix (`services/recurring.py::_size_trade`). Option `whole_shares` (PEA : le courtier n'exécute que des parts entières) : quantité arrondie à l'entier inférieur et `amount` du versement = parts × cours ; la sortie bancaire reste au montant prévu (le reliquat reste en espèces chez le courtier, comme dans la réalité) ; montant < prix d'une part → quantité fractionnaire. Le cours de clôture reste une estimation : l'exécution réelle du courtier peut différer de ~1 %, d'où la nécessité de contrôler le montant versé face à l'export du courtier.
- Abonnements détectés dynamiquement (`/analytics/subscriptions`), ignorables (`is_subscription_ignored`).
- Salaire : `salary_configs` (comptes salaire/tickets, net, valeur ticket, part salarié), `telecommuting_days` (jours TT), `salary_months` (`is_generated`). `POST/DELETE /salary/generate/{year}/{month}` crée / supprime la transaction. `services/salary_generation.py` génère **une seule** transaction « Salaire » = `net_salary − nb_jours_TT × ticket_employee_share` (pas de transaction TR : les tickets sont informatifs) ; idempotent.
- Prix en heures de travail : `services/work_time.py` (taux : `domain/salary.py::hourly_rate`), `GET/PATCH /salary/work-time` → taux horaire net = `net_salary × 12 ÷ (work_days_per_year × work_hours_per_day)` (réglages `system_settings`, 218 j × 7 h par défaut, `net_salary` avant déduction TR). Le frontend divise un montant EUR par ce taux pour l'affichage (`components/ui/work-hours.tsx`, contexte `WorkTimeProvider`) : dépenses d'`AccountDetail` (nettes des remboursements, hors virements, comptes EUR), abonnements, top marchands.

## Mois de paie

`services/budget_period.py` (calcul pur : `domain/budget_period.py`) : un salaire reçu ouvre une période (jusqu'au salaire suivant) nommée d'après le mois qu'elle finance (salaire du 25 août → septembre ; nom = mois de `début + 15 j`). Tout calcul de fenêtre mensuelle doit passer par `period_bounds(db, year, month)` (jamais `datetime(year, month, 1)`), et tout regroupement par mois par `period_key_expr` (jamais `strftime("%Y-%m")`). Réglage `budget_month_mode` (`civil` | `salary`, défaut `salary`), `GET/PUT /analytics/budget-period`. Les dates et soldes ne changent pas. Bilan annuel `/wrapped` : forcé en mois civil (`civil_months()`).

## Import / export CSV

Colonnes indispensables : `Date`, `Commercant`, `Montant` (aliases d'en-têtes dans `HEADER_ALIASES`) ; `Type`, `Categorie`, `Mois`, `Note` facultatives. Montant : le séparateur décimal est le dernier de « , » / « . » (1,234.50 = 1.234,50) ; un montant signé est accepté : `Type` explicite prioritaire, sinon négatif = Sortie, positif = Entrée (le montant stocké est toujours positif). Un `Solde Initial` à 0 est accepté, pas les autres montants nuls. `POST /import/preview` (aucune écriture ; renvoie `invalid_rows`, `warnings` et, par ligne, `line` + `error`) puis `POST /import/commit` (renvoie `error_details` = `[{line, reason}]` en français ; lignes vides ignorées) ; idempotent sur `(account_id, date, amount, merchant, type)`, doublon détecté **avant** toute création de catégorie ; fichier ≤ 10 Mo ; `imports_log` ; recalcul final des soldes. Export : `GET /export/transactions.csv` (format Numbers).

## Marchands

Créer un marchand avec alias, ou ajouter un alias, rattache aussitôt les transactions non normalisées dont le libellé bancaire est cet alias (`merchants._link_matching_transactions`). Nom et alias non vides, uniques (409 sinon). Les suggestions de normalisation ignorent les virements et les catégories Investissement/Epargne.

## Centre d'Actions (`/analytics/actions`, page `Audit.tsx`)

Agrège : audit d'intégrité (`/analytics/audit`, issues avec `id` stable : `uncategorized-expenses`, `missing-merchants`, `unnormalized-merchants`, `duplicate-transactions`, `missing-initial-balances`, `stale-investment-snapshots`, `unused-categories`, `unmatched-transfers`), alertes budget (`/analytics/budget-alerts`) et suggestions de règles. `ActionItem.action_type` pilote la modale côté frontend (`link`, `modal_categorize`, `modal_rule`, `modal_snapshot`, `modal_merchant`). Les éléments écartés sont persistés (`POST /analytics/actions/dismiss`, `dismissed_insights`). Ajouter une action : voir `docs/ACTION_CENTER.md`.

## Vérification et rapprochement de compte

`accounts.last_verified_at` est mis à jour par `POST /accounts/{id}/verify` (« Rien n'a bougé » de `AccountVerificationBanner`) ou par `POST /accounts/{id}/reconcile` quand le solde saisi par l'utilisateur égale (± 0,01) le `running_balance` de fin de journée. Sinon le rapprochement (`services/reconciliation.py`, lecture seule, 60 jours avant la date) propose des pistes : doublon (même libellé, sens et montant à ≤ 3 j), ligne dont le montant égale l'écart, ligne dont l'inversion de sens comble l'écart, sinon transaction manquante. Rien n'est corrigé automatiquement.

## Hausses de prix des abonnements

`services/subscription_prices.py::detect_price_changes` (détection d'une série : `domain/subscription_prices.py::series_change`) : séries de sorties régulières (récurrence, sinon marchand canonique, sinon libellé, par compte), cadence mensuelle / trimestrielle / annuelle, hausse ≥ 0,10 et ≥ 1 % face à un montant précédent stable. Exposé dans `price_changes` de `/analytics/subscriptions` et au Centre d'Actions. Une baisse n'est pas signalée.

## Journal des décisions

Table `financial_events` (`/financial-events`) : notes datées sans effet sur aucun calcul, repères ⚑ sur la courbe de l'onglet Historique avec les faits marquants des clôtures (`month_closures.highlight`). Rangées dans leur mois civil (le libellé de `kpi-history` peut suivre le mois de paie).

## Fiscalité et enveloppes (`/tax`, page `Tax.tsx`)

`accounts.tax_wrapper` (`pea`, `per`, `cto`, `assurance_vie`, `livret_a`) et `opened_at` activent le suivi. Règles dans `domain/tax.py`, valeurs chiffrées uniquement dans `domain/tax_rules.py` (table par année, à vérifier chaque année) :

- **PEA** : versements cumulés (somme des `versement`) face à 150 k€ ; un retrait ne restitue pas de place ; retrait avant 5 ans = alerte ; alerte si le compte démarre d'un inventaire / Point Zéro (versements antérieurs non saisis, place restante surestimée).
- **PER** : versements de l'année civile **de tous les PER actifs additionnés** (plafond du foyer, une seule carte) face au plafond de déduction = 10 % des revenus pro N-1 borné entre plancher et maximum ; économie d'impôt = versé déductible × TMI.
- **Livret A** : solde actuel du compte face au plafond (alerte « plafond atteint » : les intérêts capitalisés peuvent légitimement le dépasser).
- **Livret Jeune** : idem face à 1 600 € ; l'âge (12-25 ans) n'est pas contrôlé.
- **PEE** (`pee`) : chaque `versement` est indisponible 5 ans (les `retrait` s'imputent sur les plus anciens) → total versé, bloqué, disponible, prochain déblocage ; plafond des versements volontaires de l'année = 25 % du salaire brut annuel (réglage `tax_gross_annual_salary`). Un versement dont la note contient « abondement » est l'abondement de l'employeur : il compte dans le total et le blocage, jamais dans le plafond. Aucun impôt calculé (taux de prélèvements sociaux du PEE non confirmé).
- **Assurance-vie** : ancienneté face à 8 ans et abattement annuel rappelé (seul / couple) ; la part de gain d'un rachat n'est pas calculée.
- **CTO** : seul compte concerné par le récap annuel : dividendes bruts (net + retenue, case 2DC), plus-values réalisées (3VG) ou moins-values (3VH) issues du rejeu `replay_account` (aucun appel réseau), impôt estimé au PFU par catégorie (`pfu_rate_dividends` et `pfu_rate_gains`, car la hausse de la CSG à 10,6 % s'applique dès les revenus 2025 aux plus-values mais seulement à partir du 1.1.2026 aux dividendes : en 2025, 30 % sur les dividendes et 31,4 % sur les plus-values ; 31,4 % partout en 2026 ; l'assurance-vie reste à 17,2 %) ; une perte ne compense pas les dividendes. Ventes sans coût de revient connu : signalées, jamais comptées à zéro en silence.
- Réglages (`system_settings`) : `tax_tmi_pct`, `tax_prior_year_pro_income`, `tax_household`, `tax_gross_annual_salary`.

## Revue de fin de mois (`/month-review`, page `MonthReview.tsx`)
- Clôturer = **marquer** (table `month_closures`, photo `tx_count`/`income`/`expenses`/`unresolved_count`), jamais verrouiller : imports CSV et remboursements tardifs restent possibles. `modified_since_close` compare le nombre de transactions et l'empreinte (totaux entrées/sorties par devise de compte, sans conversion) au recalcul : exact, insensible aux taux de change ; pas d'`updated_at` sur `Transaction`, donc un simple changement de catégorie n'est pas détecté (voulu).
- `transactions.is_exceptional` : la dépense reste dans les totaux officiels et `running_balance` ; seules les lectures `*_excl_exceptional` l'isolent. Les catégories « Investissement » / « Epargne » sont exclues du calcul (déjà hors `depenses_reelles`). Alertes budget et projection de fin de mois **non** concernées.
- L'étape « catégoriser » est bornée au mois (le Centre d'Actions `/analytics/actions` est global : ne pas le réutiliser tel quel).

## Taux d'épargne et résilience
`savings` (rapport mensuel, revue de mois) = `services/month_review.py::savings_basis` = revenus − dépenses réelles en vue globale : même numérateur que `taux_epargne`. Résilience (`services/analytics/budget/resilience.py::compute_resilience`, `GET /analytics/resilience`) = épargne liquide ÷ dépenses réelles moyennes des 6 derniers mois **complets** (jamais le mois en cours) ; le « fonds de sécurité » du score de santé (vue globale) l'utilise.

## « Investi du mois » (budget)
`investissements_du_mois` (vue globale) = sorties catégorisées `Investissement`/`Epargne` non virement **+ versements liés à un virement interne** (`utils.budget_versement_ids`). Un versement sans virement lié (rapatriement d'un contrat, solde initial, intéressement) n'est pas de l'argent prélevé sur les revenus : il est exclu, y compris de la catégorie virtuelle « Investissement » (`expenses-by-category`, `budget-alerts`). `depenses_reelles` ne retranche que les sorties catégorisées, jamais les versements (absents de `depenses`). Vue par compte inchangée (les versements y sont les flux du compte).

## Bilan annuel (`/wrapped`, `services/analytics/wrapped.py`)
Somme des chiffres officiels mensuels (`compute_budget`, `expenses_by_category`, `top_merchants`) pour rester identique au Dashboard. Année en cours = janvier → mois courant, comparée à N-1 sur la même période (`previous`, seulement si N-1 a des transactions). Taux d'épargne annuel = (revenus − dépenses réelles) ÷ revenus ; patrimoine début = `patrimoine_net_total` de décembre N-1. Postes : hors Investissement/Epargne. Abonnements : récurrences `Sortie` sans `transfer_to_account_id` ni catégorie épargne/investissement ; coût = échéances réelles de l'année (montant net). Heures de travail au taux horaire actuel (pas historique).

## Services externes

Frankfurter (taux), Yahoo Finance (recherche/cotations titres, profils ETF). Aucun autre appel sortant, pas de télémétrie.

## Référence

`ARCHITECTURE.md` (modèle de données et routes), `backend/CLAUDE.md`, `frontend/src/CLAUDE.md`, skills `numera-backend`, `numera-frontend`, `numera-testing`.
