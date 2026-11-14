---
name: numera-finishing
description: Use when a Numera change seems done and before saying "done" ("c'est terminé"), committing, or handing back to the user — including small fixes, refactors and doc-only changes.
---

# Numera — before saying "done"

## Principle

Done = verified by a command run **now**, docs up to date, clean commit. No claim without command output (`superpowers:verification-before-completion`).

## Checklist (in this order)

1. **Tests** — the test for the added behaviour exists and was seen failing (`numera-tdd`).
2. **Validation** depending on what changed:

   | Changed | Command |
   |---|---|
   | `backend/` | `make lint && make check-size && make dead-code && make test` |
   | `frontend/` | `make check-size && make knip && cd frontend && npm test && npm run build` (the build alone does not run the tests) |
   | both, or a file move | `make validate` |
   | SQLAlchemy model | + reviewed Alembic migration; `tests/garde_fous/test_migrations.py` green |
   | a route or a Pydantic schema | + `make api-contract` (regenerates `openapi.json` and `schema.d.ts`, to be committed); `test_openapi_routes.py` and `test_openapi_contract.py` updated deliberately |
   | performance (queries, cache, bundle, nginx) | `numera-performance` skill: before/after measurement on a large dataset, query-count test, figures and limits in the commit message |

   The pre-commit hooks (`make hooks`) replay lint, sizes and secrets at commit time: never bypass them with `--no-verify`.

   A red command = not done. Do not commit "for now".
3. **Diff reviewed** — `git diff --stat` then `git diff`: no `print`, commented-out code, `TODO` without follow-up, off-topic file, `*.db`, `.env`, secret, baseline or snapshot regenerated without justification, floating tag (GitHub Action without SHA, Docker image without digest: rule in `CLAUDE.md`).
4. **Docs in the same commit** when the code changes:

   | Change | To update |
   |---|---|
   | route, model, command | `ARCHITECTURE.md` |
   | exposable read route | `mcp-server/numera_mcp/tools/<domain>.py` + snapshot `tests/surface_snapshot.json` (+ `mcp-server/README.md`) |
   | business rule | `CLAUDE.md` (critical rules) and the `numera-expert` skill |
   | convention, location, procedure | `backend/CLAUDE.md` / `frontend/src/CLAUDE.md` / the relevant skill |
   | single-source notion | table in `numera-clean-architecture` |
   | Action Center | `docs/ACTION_CENTER.md` |

   A doc that cites a moved path is a wrong doc: `grep` the old path in `*.md` and `.claude/`. `tests/garde_fous/test_doc_paths.py` fails the suite if a file path cited in backticks in a `.md` no longer exists (partial path accepted; file produced at runtime: add it to `NOT_IN_REPO`).
5. **Commit then PR** — `main` is protected (`docs/WORKFLOW_GIT.md`): never a direct push. Branch `type/short-topic` from an up-to-date `main`, one commit per coherent change, message in English in the repository format: `type(scope): description` (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`). The body says *why*, and why a snapshot figure changes if it does. Then `git push -u origin <branch>` and `gh pr create`: the PR **title** (same format, `!` if breaking) becomes the squashed commit and the release-notes line; fill in the template without removing any section. Merge (`gh pr merge --squash`) only when `CI ok` and `Titre de PR` are green.
6. **Report** — what is verified (commands and result), what is not (e.g. visual rendering, mobile, dark mode not looked at).

## Stop signals

"It should pass" · tests run before the last change · frontend build not run after a type change · doc "to update later" · a commit that mixes a refactor and a behaviour change.
