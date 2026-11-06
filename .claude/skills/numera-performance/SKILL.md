---
name: numera-performance
description: Use when optimizing or reviewing performance in Numera — a slow route or page, a new endpoint that loops over rows, a new cache, an index question, a bundle or nginx change — and before writing any code that loads many rows, calls the database inside a loop, or caches a result.
---

# Numera — performance

## Principe

**Mesurer, corriger la cause, prouver le gain.** Une optimisation sans chiffre avant/après est une opinion. La base réelle est petite (≈ 200 transactions) : tout y est instantané, donc les problèmes se voient seulement sur un jeu volumineux. Procédure de test : `numera-tdd` ; où va le code : `numera-clean-architecture` ; validation : `numera-finishing`.

## 1. Mesurer d'abord

```bash
cd backend && export PYTHONPATH=.
python3.11 scripts/perf_profile.py seed --db /tmp/perf_demo.db --months 240 --multiply 6   # ≈ 50 000 transactions
python3.11 scripts/perf_profile.py bench --db /tmp/perf_demo.db                              # toutes les routes GET, les plus lentes d'abord
python3.11 scripts/perf_profile.py profile --db /tmp/perf_demo.db /analytics/audit           # requêtes SQL + fonctions coûteuses
```

- Le nom de la base contient « demo » (garde `DEMO_MODE`) : jamais `backend/data/suivi_budget.db`. Bases temporaires dans le scratchpad ou `/tmp`.
- `bench` garde le meilleur de deux appels : le second profite des caches. Pour un coût à froid, `profile` (un appel de chauffe puis un appel mesuré, profileur actif donc durées gonflées : lire les proportions).
- Lire d'abord le **nombre de requêtes SQL** : des centaines de requêtes de quelques ms = N+1 ; peu de requêtes mais beaucoup de temps = objets ORM instanciés ou calcul Python.
- Navigateur : octets transférés, requêtes, temps du Dashboard à froid et au retour (Chromium/Playwright ou navigateur intégré). Un `localhost` ne mesure pas un vrai réseau : le dire.

Références mesurées le 2026-11-01 (44 600 transactions) : audit 117 ms, suggestions de virements 279 ms, export CSV 473 ms ; Dashboard à froid 2 171 → 739 ms, 1 230 → 394 Ko transférés, retour sur le Dashboard 0 requête. Une route qui dépasse ces ordres de grandeur sur le même jeu est une régression.

## 2. Backend : règles

| Situation | Règle | Modèle dans le code |
|---|---|---|
| Une requête par ligne d'une boucle (`db.query/get` dans un `for`) | Charger en **une** requête les candidats pour tout le lot, apparier en mémoire (fonction pure dans `domain/`) | `repositories/analytics/audit.py::strict_transfer_candidates` + `domain/transfers.py::strict_matches` |
| Lecture seule de beaucoup de lignes (export, appariement) | Requêter des **colonnes** (`db.query(M.a, M.b)`), pas des objets ORM (chaque objet charge ses relations `selectin`) ; recharger en entier seulement les lignes retenues | `repositories/budget/exports.py`, `MATCH_COLUMNS` + `load_legs` dans `repositories/budget/transfers.py` |
| `async def` | Seulement s'il y a un `await`. Une coroutine qui travaille en synchrone **bloque tout le serveur** ; garde-fou : `tests/garde_fous/test_async_endpoints.py` | — |
| Résultat coûteux relu par plusieurs routes | Cache bref **invalidé par les écritures** (voir §3), jamais un cache « au cas où » | `services/investissement/portfolio/cache.py` |
| « Il faudrait un index » | `EXPLAIN QUERY PLAN` d'abord ; corriger le N+1 avant. Les clés étrangères, `date`, `merchant` sont déjà indexées. Un index composite ne s'ajoute (migration Alembic, `test_migrations.py`) que si le plan montre un scan complet sur une requête **unique** et lente | — |
| Recalcul intégral des soldes (`recalculate_running_balances`, O(n) par écriture) | Lecture par colonnes + `UPDATE` en masse des seules lignes modifiées (1 requête, 0,2 s à 44 000 transactions) ; jamais d'objets ORM (7 relations `selectin`) | `repositories/budget/balances.py` |
| Appel réseau (Yahoo, Frankfurter) | Cache négatif + disjoncteur + concurrence bornée ; route `def` qui appelle le service par `run_async` | `core/circuit_breaker.py`, `core/sync_bridge.py`, `market/quotes.py` |

Chaque correctif backend vient avec un **test de nombre de requêtes** : fixture `measure_queries` (`tests/conftest.py`) sur un jeu volumineux (≥ 1 000 lignes), borne large mais qui échoue au N+1 (modèles : `tests/audit/test_data_audit_transfers.py`, `tests/budget/test_export_queries.py`, `tests/budget/test_potential_transfers_queries.py`). Le test passe d'abord au rouge sur l'ancien code, pour la bonne raison (le nombre de requêtes, pas une erreur d'import). Le résultat renvoyé reste identique : instantanés intacts.

## 3. Ajouter un cache : cahier des charges

Un cache est un risque de donnée périmée. Il faut **tous** ces points, chacun testé :

1. Durée courte (`TTL`), clé complète (compte, options, base : `id(db.get_bind())`).
2. **Invalidation sur écriture** : `after_flush` et `after_commit` de `Session`, toutes sessions et tâches de fond confondues. Écriture par connexion brute (`exec_driver_sql`) : appeler `invalidate()`.
3. **Génération** : un calcul démarré avant une écriture ne s'enregistre pas (sinon il remet l'ancien état dans le cache).
4. **Copie profonde** à l'entrée et à la sortie : l'appelant peut modifier ce qu'il reçoit.
5. Une fixture `autouse` de `conftest.py` le vide entre deux tests (ids de moteur réutilisés).
6. Tests : 2ᵉ appel sans requête SQL, écriture invalide, flush sans commit invalide, modification de la copie sans effet, erreur non mémorisée (modèle : `tests/investissement/test_portfolio_cache.py`).

## 4. Frontend et exploitation

- **Lecture** : `api.get` ressert 30 s la même URL et dédoublonne (`lib/apiCache.ts`). Toute écriture, la déconnexion et un 401 invalident. Un bouton « Actualiser » / « Réessayer » ou un `reload()` qui **relit sans écrire** appelle `resetApiCache()` d'abord, avec un test rouge qui compte les requêtes (modèle : `pages/Audit/Audit.test.tsx`). `queryClient.clear()` est interdit : il annule les lectures en vol (`CancelledError`).
- **Bundle** : `manualChunks` dans `vite.config.ts`. Après une nouvelle dépendance ou un nouvel import, vérifier les `modulepreload` de `dist/index.html` : les graphiques (`vendor-charts`, ~120 Ko gzip) ne doivent pas y figurer. Un utilitaire partagé avec recharts (`clsx`…) se range dans `vendor-ui`. Comparer `npm run build` avant/après (octets gzip du chargement initial).
- **nginx** (`frontend/nginx.conf`) : `gzip` actif sauf `/api/auth/` (BREACH) ; ne pas l'ajouter au flux MCP. Vérification : `docker run --rm --add-host backend:127.0.0.1 --add-host mcp-server:127.0.0.1 -v $PWD/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro nginx:alpine nginx -t`, puis `curl -H 'Accept-Encoding: gzip' -I` sur un fichier de `dist/assets/`.
- **Aucun calcul de KPI côté frontend** pour « gagner du temps » : règle critique n° 2.

## 5. Terminer

`make validate` (lint, types, tailles, couverture, tests, build). Le message de commit donne les chiffres (`perf(audit): … ~1 s → ~130 ms à 44 000 transactions`) et les limites de la mesure. Si un nouveau cache ou une nouvelle règle de performance est ajouté, mettre à jour `backend/CLAUDE.md` / `frontend/src/CLAUDE.md` et ce skill dans le même commit.

## Rationalisations

| Excuse | Réalité |
|---|---|
| « C'est sûrement l'index qui manque » | Sur ce code, c'était un N+1 : 251 requêtes de 4 ms. L'index n'aurait rien changé au nombre de requêtes. |
| « Je cache le résultat, ce sera plus rapide » | Sans invalidation sur écriture, c'est une donnée fausse pendant la durée du cache. Cahier des charges §3. |
| « Ma base de dev est instantanée » | 220 transactions. Mesurer sur le jeu volumineux de `perf_profile.py seed`. |
| « Je passe en `async` pour que ça ne bloque pas » | `async def` sans `await` bloque davantage. |
| « Je régénère l'instantané, le chiffre a bougé » | Une optimisation ne change aucun chiffre. Un écart d'instantané est un bug. |
| « Le gain est évident, pas besoin de mesurer après » | Le premier découpage du bundle chargeait les graphiques dès l'entrée : plus lourd qu'avant. Toujours rejouer la mesure. |
| « Un `reload()` n'a pas besoin de test » | Il resservirait la réponse en cache. Test qui compte les requêtes. |

## Signaux d'arrêt

`db.query` / `db.get` dans une boucle · `.all()` d'objets ORM pour n'en lire que quelques colonnes · `async def` sans `await` · cache sans invalidation sur écriture ou sans copie · index ajouté sans `EXPLAIN QUERY PLAN` · `queryClient.clear()` · bouton « Actualiser » qui relit via le cache · optimisation annoncée sans chiffre avant/après · instantané régénéré.
