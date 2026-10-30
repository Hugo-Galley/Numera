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
   | `backend/` | `make lint && make check-size && make test` |
   | `frontend/` | `make check-size && cd frontend && npm test && npm run build` (le build seul ne lance pas les tests) |
   | les deux, ou un déplacement de fichier | `make validate` |
   | modèle SQLAlchemy | + migration Alembic relue ; `tests/test_migrations.py` vert |
   | une route | + `tests/test_openapi_routes.py` mis à jour volontairement |

   Une commande rouge = pas terminé. Ne pas commiter « en attendant ».
3. **Diff relu** — `git diff --stat` puis `git diff` : pas de `print`, de code commenté, de `TODO` sans suite, de fichier hors sujet, de `*.db`, de `.env`, de secret, de baseline ou d'instantané régénéré sans justification.
4. **Docs dans le même commit** quand le code change :

   | Changement | À mettre à jour |
   |---|---|
   | route, modèle, commande | `ARCHITECTURE.md` |
   | route de lecture exposable | `mcp-server/server_api.py` (+ `mcp-server/README.md`) |
   | règle métier | `CLAUDE.md` (règles critiques) et skill `numera-expert` |
   | convention, emplacement, procédure | `backend/CLAUDE.md` / `frontend/src/CLAUDE.md` / skill concerné |
   | notion à source unique | tableau de `numera-clean-architecture` |
   | Centre d'Actions | `docs/ACTION_CENTER.md` |

   Une doc qui cite un chemin déplacé est une doc fausse : `grep` l'ancien chemin dans `*.md` et `.claude/`.
5. **Commit** — directement sur `main`, un commit par changement cohérent, message en français au format du dépôt : `type(portée): description` (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`). Le corps dit *pourquoi*, et pourquoi un chiffre d'instantané change si c'est le cas.
6. **Compte rendu** — ce qui est vérifié (commandes et résultat), ce qui ne l'est pas (ex. rendu visuel, mobile, mode sombre non regardés).

## Signaux d'arrêt

« Ça devrait passer » · tests lancés avant la dernière modification · build frontend non lancé après un changement de type · doc « à mettre à jour plus tard » · commit qui mélange refactor et changement de comportement.
