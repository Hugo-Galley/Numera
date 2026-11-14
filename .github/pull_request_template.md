<!--
The PR TITLE becomes the commit message (squash merge) and feeds the release notes.
Required format: type(scope): description   e.g. fix(budget): rounding of the current balance
Types: feat fix perf refactor test docs build ci chore revert style · `!` before `:` = breaking change
-->

## Why

<!-- The problem or the need, not the list of modified files. Link the issue: "Closes #123". -->

## What changes

<!-- Visible behaviour, design decisions, discarded alternatives. -->

## Areas touched

- [ ] Backend
- [ ] Frontend
- [ ] Alembic migration
- [ ] Docker / CI / workflows
- [ ] Docs / skills only

## Verification

<!-- What was run and its result (command + useful output). What was NOT verified, stated frankly. -->

- [ ] `make validate` green locally
- [ ] Failing test written before the code (backend, skill `numera-tdd`)
- [ ] Rendering checked by hand: light/dark, mobile, privacy mode (if UI)

## Checklist

- [ ] `ARCHITECTURE.md`, `CLAUDE.md` or the relevant skill updated (route, model, command, business rule)
- [ ] No ratchet threshold lowered (coverage, sizes, ESLint) and no baseline raised
- [ ] No floating tag: actions pinned by SHA, images by digest
- [ ] Reversible migration, tested on an existing database (if schema changed)
- [ ] Before/after measurements in this description (if optimisation, skill `numera-performance`)
- [ ] A single topic: no refactor mixed with a behaviour change

## Risks and rollback

<!-- Irreversible migration, data format change, new environment variable? Otherwise "none". -->
