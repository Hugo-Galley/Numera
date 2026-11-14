---
name: numera-finishing
description: Use when a Numera change seems done and before saying "c'est terminé", committing, or handing back to the user — including small fixes, refactors and doc-only changes.
---

# Numera — avant de dire « terminé »

## Principe

Terminé = vérifié par une commande lancée **maintenant**, docs à jour, commit propre. Pas d'affirmation sans sortie de commande (`superpowers:verification-before-completion`).

## Checklist (dans cet ordre)

1. **Tests** — le test du comportement ajouté existe et a été vu rouge (`numera-tdd`).
2. **Validation** selon ce qui a changé :

   | Changé | Commande |
   |---|---|
   | `backend/` | `make lint && make check-size && make dead-code && make test` |
   | `frontend/` | `make check-size && make knip && cd frontend && npm test && npm run build` (le build seul ne lance pas les tests) |
   | les deux, ou un déplacement de fichier | `make validate` |
   | modèle SQLAlchemy | + migration Alembic relue ; `tests/garde_fous/test_migrations.py` vert |
   | une route ou un schéma Pydantic | + `make api-contract` (régénère `openapi.json` et `schema.d.ts`, à commiter) ; `test_openapi_routes.py` et `test_openapi_contract.py` mis à jour volontairement |
   | performance (requêtes, cache, bundle, nginx) | skill `numera-performance` : mesure avant/après sur jeu volumineux, test de nombre de requêtes, chiffres et limites dans le message de commit |

   Les hooks pre-commit (`make hooks`) rejouent lint, tailles et secrets au commit : ne jamais les contourner avec `--no-verify`.

   Une commande rouge = pas terminé. Ne pas commiter « en attendant ».
3. **Diff relu** — `git diff --stat` puis `git diff` : pas de `print`, de code commenté, de `TODO` sans suite, de fichier hors sujet, de `*.db`, de `.env`, de secret, de baseline ou d'instantané régénéré sans justification, de tag flottant (action GitHub sans SHA, image Docker sans digest : règle dans `CLAUDE.md`).
4. **Docs dans le même commit** quand le code change :

   | Changement | À mettre à jour |
   |---|---|
   | route, modèle, commande | `ARCHITECTURE.md` |
   | route de lecture exposable | `mcp-server/numera_mcp/tools/<domaine>.py` + snapshot `tests/surface_snapshot.json` (+ `mcp-server/README.md`) |
   | règle métier | `CLAUDE.md` (règles critiques) et skill `numera-expert` |
   | convention, emplacement, procédure | `backend/CLAUDE.md` / `frontend/src/CLAUDE.md` / skill concerné |
   | notion à source unique | tableau de `numera-clean-architecture` |
   | Centre d'Actions | `docs/ACTION_CENTER.md` |

   Une doc qui cite un chemin déplacé est une doc fausse : `grep` l'ancien chemin dans `*.md` et `.claude/`. `tests/garde_fous/test_doc_paths.py` fait échouer la suite si un chemin de fichier cité entre accents graves dans un `.md` n'existe plus (chemin partiel accepté ; fichier produit à l'exécution : l'ajouter à `NOT_IN_REPO`).
5. **Commit puis PR** — `main` est protégée (`docs/WORKFLOW_GIT.md`) : jamais de push direct. Branche `type/sujet-court` depuis `main` à jour, un commit par changement cohérent, message en français au format du dépôt : `type(portée): description` (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`). Le corps dit *pourquoi*, et pourquoi un chiffre d'instantané change si c'est le cas. Puis `git push -u origin <branche>` et `gh pr create` : le **titre** de la PR (même format, `!` si incompatible) devient le commit squashé et la ligne des notes de version ; remplir le template sans en supprimer de section. Merge (`gh pr merge --squash`) seulement quand `CI ok` et `Titre de PR` sont verts.
6. **Compte rendu** — ce qui est vérifié (commandes et résultat), ce qui ne l'est pas (ex. rendu visuel, mobile, mode sombre non regardés).

## Signaux d'arrêt

« Ça devrait passer » · tests lancés avant la dernière modification · build frontend non lancé après un changement de type · doc « à mettre à jour plus tard » · commit qui mélange refactor et changement de comportement.
