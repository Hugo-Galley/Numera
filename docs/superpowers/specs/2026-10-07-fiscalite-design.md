# Fiscalité et enveloppes françaises : conception

Date : 2026-10-07 · Statut : à relire

## Objectif

Donner à Numera la connaissance des règles des enveloppes françaises détenues par l'utilisateur
(PEA, PER, CTO, assurance-vie, Livret A) : plafonds et place restante, dates clés, et récapitulatif
fiscal annuel du CTO. Une page dédiée `/tax` « Fiscalité ».

Mono-utilisateur, self-hosted, aucune notification : la page est consultée à la main.

## Approche

Calcul à la volée côté backend (comme les autres KPI de `api/analytics/`), à partir des versements,
soldes, dividendes et plus-values déjà en base. Aucun instantané stocké. Les règles (plafonds, seuils)
sont des constantes versionnées par année dans `core/tax_rules.py`.

## Modèle de données

Migration Alembic : deux colonnes nullable sur `accounts`.

- `tax_wrapper` : `pea` | `per` | `cto` | `assurance_vie` | `livret_a`. Un compte sans valeur est ignoré par la page.
- `opened_at` : date d'ouverture (5 ans PEA, 8 ans AV).

Trois réglages dans `system_settings` (clés) : `tax_tmi`, `tax_prior_year_pro_income`, `tax_household`
(`single` | `couple`). Valeurs par défaut quand rien n'est saisi.

Les schémas de compte (`schemas/`) et le `PATCH /accounts/{id}` exposent `tax_wrapper` et `opened_at` ;
l'UI les édite dans les paramètres de compte, à côté du mode de valorisation.

## Règles par enveloppe (`core/tax_rules.py`)

| Enveloppe | Calcul |
|---|---|
| PEA | Versements cumulés (somme des `versement`, les retraits ne restituent pas de place) vs 150 000 €. Âge du plan ; alerte si un retrait a lieu avant 5 ans. |
| PER | Versements de l'année civile vs plafond de déduction = 10 % des revenus pro N-1, borné entre un plancher et un maximum. Économie d'impôt estimée = versé × TMI. |
| Livret A | Solde actuel vs 22 950 €, place restante (jamais négative). |
| Assurance-vie | Ancienneté vs 8 ans ; abattement annuel rappelé (4 600 € seul, 9 200 € couple). Pas de calcul de la part de gain d'un rachat. |
| CTO | Par année : dividendes (case 2DC) et plus-values réalisées (case 3VG), impôt estimé au PFU, avec deux taux distincts (dividendes / plus-values) selon l'année, cf. `core/tax_rules.py` (en 2025 : 30 % et 31,4 % ; en 2026 : 31,4 %). Seuls les comptes `cto` comptent (ni PEA ni AV). |

Les plafonds officiels changent chaque année : table par année, valeurs à faire vérifier par
l'utilisateur avant mise en service. Aucune valeur non confirmée codée en dur ailleurs que dans cette table.

Sources de données : `investment_transactions` (versements), `core/dividends.py` (`load_dividends_eur`),
`core/portfolio.py` (plus-values réalisées par année), solde du compte (`core/finance.py`).

## API (`api/tax.py`, ajouté à `protected_routers`)

- `GET /tax/overview` : une carte par enveloppe (courant, plafond, place restante, alertes).
- `GET /tax/annual-report?year=` : récap CTO de l'année (lignes dividendes/plus-values avec case, totaux, impôt estimé PFU).
- `GET/PATCH /tax/settings` : TMI, revenus pro N-1, foyer.

Calculs dans `api/analytics/tax.py` (KPI côté backend uniquement, règle métier 2).

## Frontend (`pages/Tax.tsx`, route `/tax`, entrée de menu)

- Bandeau de réglages repliable.
- Grille de cartes à jauge : PEA, PER, Livret A, AV (ancienneté).
- Section « Déclaration » : sélecteur d'année, tableau 2DC / 3VG du CTO.
- Mode confidentialité respecté. Compte sans `tax_wrapper` : message vers les paramètres de compte.

## Tests (pytest, DB temporaire)

- PEA : un retrait ne libère pas de place ; dépassement de plafond = alerte.
- PER : plafond borné plancher/maximum ; économie = versé × TMI.
- Livret A : place restante correcte ; solde > plafond sans exception.
- CTO : regroupement par année ; PEA et AV exclus.
- Settings : valeurs par défaut sans saisie.
- Le router exige le JWT.

## Documentation

Même commit : `ARCHITECTURE.md` (routes, modèle), skill `numera-expert` (règles), `mcp-server/server_api.py`
si une route est exposable.

## Hors périmètre

Part de gain d'un rachat d'AV, impôt complet par tranches, PEA-PME, LDDS, LEP, crypto.
