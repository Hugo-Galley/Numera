---
name: numera-clean-architecture
description: Use when deciding where new Numera code goes (controller, service, repository, domain, integration, frontend), when moving or splitting a file, when a calculation might already exist elsewhere, or when test_architecture.py / check_code_size.py fails.
---

# Numera — clean architecture

## Principe

Une responsabilité par couche, une définition par règle métier. Les garde-fous (`tests/garde_fous/test_architecture.py`, `scripts/check_code_size.py`) attrapent les imports et les tailles ; ce skill couvre ce qu'ils ne voient pas. Règles d'import détaillées : `backend/CLAUDE.md` § Couches.

## Où va ce code ?

| Le code… | Couche | Interdit |
|---|---|---|
| lit la requête HTTP, choisit le code d'erreur 401/403/413/429 | `controllers/<domaine>/` — une ligne qui appelle un service | logique, requête SQL, `commit` |
| orchestre un cas d'usage, `commit`, lève une erreur métier | `services/<domaine>/` | `fastapi`, `HTTPException`, importer un controller |
| interroge la base | `repositories/<domaine>/` | `commit`, appeler un service |
| calcule (montant, date, agrégat, classement) sans I/O | `domain/` | `Session`, `sqlalchemy.orm`, réseau |
| parle au réseau (Yahoo, Frankfurter, ntfy) | `integrations/` | logique métier |
| affiche | `frontend/src/` | tout KPI, total, ratio, statut calculé |

Un calcul dans un service qu'on ne peut tester qu'avec une base → l'extraire dans `domain/` et le tester en mémoire (`numera-tdd`).

## Une seule définition (source de vérité)

Les audits A1–A12 venaient presque tous de la **même règle codée deux fois** qui divergeait. Avant d'écrire un calcul, chercher l'existant :

```bash
grep -rn "def .*<mot-clé>" backend/app/domain backend/app/services backend/app/repositories
```

| Notion | Source unique |
|---|---|
| Revenu | `repositories/analytics/common.py::income_criterion` |
| Valeur de compte / patrimoine | `services/comptes/wealth.py::account_values` |
| Soldes courants | `services/budget/balances.py::recalculate_running_balances` |
| Positions titres | `services/investissement/holdings/rebuild.py::rebuild_holdings` |
| Valorisation portefeuille | `services/investissement/portfolio/compute.py::compute_portfolio` |
| Budget | `services/analytics/budget/summary.py::compute_budget` (appeler le service, jamais une fonction de route) |
| Salaire | `domain/salary.py::salary_amount` |
| Format d'un montant (front) | `lib/utils.ts::formatCurrency` |

Besoin d'une variante ? Paramétrer la fonction existante, ne pas la copier. Une nouvelle notion transverse → l'ajouter à ce tableau.

## Déplacer ou découper du code

1. Tests verts avant de commencer ; le déplacement ne change aucun test sauf ses imports.
2. Mettre à jour **tous** les importeurs : absolus, relatifs, imports locaux dans les fonctions, `monkeypatch.setattr("ancien.module…")`, scripts (`scripts/`, `backend/scripts/`, `Makefile`, `docker-compose*.yml`, `infra/`).
3. Aucun ré-export depuis l'ancien emplacement ; supprimer l'ancien fichier.
4. Vérifier les chemins hors Python : `grep -rn "ancien/chemin\|ancien\.module" --exclude-dir=node_modules .` (les correctifs « demo » et « backup » venaient d'un déplacement oublié dans `Makefile`/script).
5. Un domaine n'importe pas le controller d'un autre domaine : passer par le service.

## Cliquets (baselines)

`tests/garde_fous/architecture_baseline.txt` et `scripts/code_size_baseline.json` ne font que **diminuer**. Une violation nouvelle se corrige dans le code (découper, déplacer), jamais en régénérant la baseline. Régénérer n'est permis que pour retirer une entrée disparue ou renommer une clé lors d'un déplacement à l'identique.

## Rationalisations

| Excuse | Réalité |
|---|---|
| « Juste un petit calcul dans le router » | Le router devient intestable et le calcul sera recopié ailleurs. Service ou `domain/`. |
| « Je calcule le total côté front, c'est de l'affichage » | Un total est un KPI. Backend (règle critique n° 2). |
| « Je duplique pour ne pas casser l'existant » | La duplication *est* le bug futur. Paramétrer, tests à l'appui. |
| « Je ré-exporte pour la compatibilité » | Interdit. Mettre à jour les importeurs. |
| « J'ajoute la ligne à la baseline, je découperai plus tard » | Plus tard n'arrive pas. Découper maintenant. |
| « `HTTPException` dans le service, c'est plus direct » | Erreurs de `core/errors.py` ; le handler les traduit. |

## Signaux d'arrêt

Import de `fastapi` hors `controllers/` · `db.commit()` dans un repository · arithmétique sur des montants dans un `.tsx` · deux fonctions qui calculent la même notion · fichier régénéré dans `*baseline*` · ancien module laissé « au cas où ».
