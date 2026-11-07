# Git workflow: PRs are mandatory

`main` is protected: no more direct pushes, everything goes through a pull request with green checks. The rules are versioned (`.github/rulesets/`) and applied by `scripts/ci/github_rules.sh`.

## Lifecycle of a change

1. **Start from an up-to-date `main`**, create a branch: `type/short-topic` (`feat/export-pdf`, `fix/current-balance`, `docs/git-workflow`). One topic per branch.
2. **Commit** as usual (Conventional Commits, body = why). Commits on the branch are free-form: only the PR title matters (squash).
3. **Validate locally**: `make validate` (skill `numera-finishing`). Once per clone, `make hooks` installs the git safeguards (`.pre-commit-config.yaml`): on commit gitleaks (secrets), ruff and size caps; on push mypy and the frontend typecheck. They replay CI checks earlier, they do not replace them; `make pre-commit-all` runs them on the whole repository.
4. **Push and open the PR**: `gh pr create --fill-first`, then complete the template. The **title** follows `type(scope): description` (the "Titre de PR" check, i.e. PR title), because it becomes the commit on `main` and the line in the release notes. Breaking change: `!` before `:` (`feat(api)!: …`).
5. **Wait for the checks**: `CI ok` (backend, frontend, e2e, hadolint, Trivy repo and images) and `Titre de PR`. Hadolint and the image scans only run if the PR touches what makes up the images (Dockerfile, dependencies, `nginx.conf`, `.trivyignore.yaml`, `ci.yml`: list in `scripts/ci/ci_changes.py`, verified by `tests/garde_fous/test_ci_changes.py`); on `main` and on release, everything is scanned. The branch does **not** need to be up to date with `main` (the ruleset no longer requires `strict_required_status_checks_policy`): a green PR is merged as is, with no rebase and no new CI run. Conversations must be resolved.
6. **Squash merge** (the only allowed method). The branch is deleted automatically. `gh pr merge --squash --auto` merges as soon as the checks pass.

No mandatory review (single-user repository: you cannot approve your own PR). The safeguard is the checks and the template.

## What is enforced (rulesets)

| Target | Rules |
|---|---|
| `main` and `release/**` | PR required · squash only · linear history · `CI ok` (including `Cliquets`: no baseline raised and no coverage threshold lowered compared with the base, `scripts/quality/check_ratchets.py`) + `Titre de PR` checks required (no obligation to be up to date with `main`) · conversations resolved · no force-push or deletion · no bypass |
| `v*` tags | no deletion or move: a published version is immutable |

`CI ok` is an aggregate job of `ci.yml`: it is the only one required, so the list of jobs can change without touching the rules. To change a rule: edit the JSON in `.github/rulesets/`, go through a PR, then rerun `scripts/ci/github_rules.sh` (admin).

In an absolute emergency (CI broken by GitHub itself), temporarily disable the ruleset in Settings → Rules, merge, **re-enable it**, and say so in the PR.

## Releases and `release/X.Y` branches

Common case: tag `main` (`make release V=X.Y.Z`, skill `numera-release`). No permanent release branch: only one version is supported (the latest), and it would cost cherry-picks for nothing.

A `release/X.Y` branch is created **only on demand**, when `main` has already moved on with changes you do not want to ship and a published version needs a fix:

```bash
git switch -c release/0.2 v0.2.0 && git push -u origin release/0.2
```

The fix is made on `main` first (normal PR), then back-ported through a PR to `release/0.2` (`git cherry-pick -x <sha>`), with a title starting with `fix(...)`. Once merged, run `make release V=0.2.1` from `release/0.2` (the `release.yml` workflow accepts a tag that is on `main` or on `release/*`). `:latest` and the "Latest release" do not move for this tag (only the highest version carries them). The branch is protected like `main`. (Untested: if the ruleset refuses branch creation via `git push`, create it with `gh api repos/Hugo-Galley/numera/git/refs` or briefly disable the `release/*` ruleset, then correct this page.)

## Dependabot

Dependabot PRs (prefix `build(deps)`) follow the same path: green checks, squash. Read a major version bump before merging.

## Why the branch does not need to be up to date with `main`

Requiring "up to date" (strict mode) forces a rebase and then a full CI run (4 to 6 min) on every open PR after each merge: with 4 PRs, 4 cycles in a row. GitHub's merge queue, which solves this problem, does not exist for a personal-account repository. The accepted cost: a PR is tested on its base, not on the exact result of the merge, so two green PRs that contradict each other semantically (without a text conflict) can break `main`. The safety net: CI also runs on every push to `main` (`ci.yml`), and a red `main` is fixed immediately by a PR. If it happens more than once, go back to strict mode (set `true` again in `.github/rulesets/*.json` and rerun `scripts/ci/github_rules.sh`).
