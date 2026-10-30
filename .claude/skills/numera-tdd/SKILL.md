---
name: numera-tdd
description: Use when about to write or change backend code in Numera (feature, bug fix, KPI, règle d'audit, import, refactor de comportement), before touching backend/app/, or when tempted to "tester après" / "juste corriger vite".
---

# Numera — TDD obligatoire

## Principe

**Aucune ligne de `backend/app/` sans un test qui échoue d'abord, pour la bonne raison.**
Violer la lettre de cette règle, c'est violer son esprit. Cycle complet : `superpowers:test-driven-development` ; ce skill dit comment l'appliquer ici.

## Le cycle dans Numera

1. **RED** — écrire le test, le lancer seul, le voir échouer :
   ```bash
   cd backend && PYTHONPATH=. python3.11 -m pytest tests/<domaine>/test_<sujet>.py::test_<cas> -v
   ```
   L'échec doit être une **assertion** sur le comportement attendu (pas `ImportError`, pas `401`, pas une fixture cassée). Un test qui passe du premier coup ne prouve rien : le corriger ou en écrire un autre.
2. **GREEN** — le code minimal qui fait passer ce test. Rien d'autre.
3. **REFACTOR** — nettoyer (couches, noms, duplication), tests verts à chaque pas. Puis suite complète : `make test`.

## Quel niveau de test

| Ce que tu changes | Où va le test | Fixture |
|---|---|---|
| Calcul pur (`domain/`) | `tests/<domaine>/test_domain_<sujet>.py` | aucune : objets en mémoire (modèle : `test_domain_transfers.py`) |
| Cas d'usage (`services/`) | `tests/<domaine>/test_<sujet>_service.py` | `db_session`, sans HTTP |
| Contrat d'une route | `tests/<domaine>/test_<sujet>.py` | `client` + relecture en base |
| Chiffre analytics / portefeuille | test ciblé **en plus** des instantanés | — |

Le niveau le plus bas qui exprime le comportement gagne. Un calcul difficile à tester sans base est un calcul qui n'est pas encore dans `domain/` : c'est le test qui te dit où le mettre (cf. `numera-clean-architecture`).

## Assertions qui comptent

- Effet en base, pas seulement le code HTTP. Pour un commit attendu, relire dans une **session neuve** (`_fresh_balances` dans `test_balances_service.py`).
- Soldes (`running_balance`) après toute mutation de transaction ; positions après toute opération titres.
- Dates figées (`freezegun`) dès qu'un calcul dépend d'« aujourd'hui ».
- Réseau : interdit en test (`block_network`). Patcher `integrations/…`, jamais désactiver le garde.

## Bug = test de reproduction d'abord

Bug signalé → `superpowers:systematic-debugging` pour la cause, puis un test qui **reproduit** le bug et échoue, puis le correctif. Nommer le test d'après le comportement (`test_transfer_between_same_account_is_never_paired`), pas d'après le ticket.

## Instantanés (`tests/snapshots/`)

Un écart d'instantané est un test rouge comme un autre. Jamais `UPDATE_SNAPSHOTS=1` pour faire passer la suite. Seulement quand le changement de chiffre est **voulu** : un test ciblé démontre d'abord le nouveau chiffre, puis régénération, et le commit dit pourquoi le chiffre change.

## Frontend

Les tests frontend (Vitest, skill `numera-testing`) vérifient le rendu, les appels et les parcours, pas des règles métier : aucune logique n'y vit. Une règle à tester côté front (calcul, agrégat, statut) → elle appartient au backend, en TDD. Un bug frontend corrigé suit la même discipline : test `X.test.tsx` rouge d'abord.

## Rationalisations

| Excuse | Réalité |
|---|---|
| « Trop simple pour un test » | Les audits A2–A12 étaient des « simples » calculs dupliqués. 30 s de test. |
| « J'écris les tests après » | Un test écrit après passe immédiatement : il ne prouve rien. |
| « Le snapshot couvre déjà ça » | Le snapshot dit *que* ça change, pas *ce qui* est juste. Test ciblé. |
| « C'est un refactor, pas de comportement » | Alors les tests existants doivent rester verts sans modification. S'il faut les changer, c'est un changement de comportement → RED d'abord. |
| « J'ai testé à la main dans l'UI » | Non reproductible, non versionné. Écris le test. |
| « Je garde le code déjà écrit comme référence » | Supprime-le. Repars du test. |
| « L'utilisateur est pressé » | Un correctif sans test revient en audit. Le test *est* le chemin rapide. |

## Signaux d'arrêt

Code écrit avant le test · test jamais vu rouge · test rouge pour une mauvaise raison · instantané régénéré sans test ciblé · « je testerai à la fin ». → Supprimer le code, revenir au RED.
