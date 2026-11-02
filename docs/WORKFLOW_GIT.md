# Workflow Git : PR obligatoire

`main` est protégée : plus aucun push direct, tout passe par une pull request dont les checks sont verts. Les règles sont versionnées (`.github/rulesets/`) et appliquées par `scripts/github_rules.sh`.

## Cycle d'un changement

1. **Partir de `main` à jour**, créer une branche : `type/sujet-court` (`feat/export-pdf`, `fix/solde-courant`, `docs/workflow-git`). Un sujet par branche.
2. **Commiter** comme avant (Conventional Commits, corps = pourquoi). Les commits de la branche sont libres : seul le titre de la PR compte (squash).
3. **Valider en local** : `make validate` (skill `numera-finishing`). Une fois par clone, `make hooks` installe les garde-fous git (`.pre-commit-config.yaml`) : au commit gitleaks (secrets), ruff et plafonds de taille, au push mypy et typecheck frontend. Ils rejouent des contrôles de la CI plus tôt, ils ne les remplacent pas ; `make pre-commit-all` les lance sur tout le dépôt.
4. **Pousser et ouvrir la PR** : `gh pr create --fill-first` puis compléter le template. Le **titre** respecte `type(portée): description` (check « Titre de PR »), car il devient le commit sur `main` et la ligne des notes de version. Changement incompatible : `!` avant `:` (`feat(api)!: …`).
5. **Attendre les checks** : `CI ok` (backend, frontend, e2e, hadolint, Trivy repo et images) et `Titre de PR`. Hadolint et les scans d'images ne tournent que si la PR touche ce qui compose les images (Dockerfile, dépendances, `nginx.conf`, `.trivyignore.yaml`, `ci.yml` : liste dans `scripts/ci_changes.py`, vérifiée par `tests/garde_fous/test_ci_changes.py`) ; sur `main` et en release, tout est scanné. La branche n'a **pas** besoin d'être à jour avec `main` (le ruleset n'exige plus `strict_required_status_checks_policy`) : une PR verte se merge telle quelle, sans rebase ni nouvelle CI. Les conversations doivent être résolues.
6. **Merger en squash** (seule méthode autorisée). La branche est supprimée automatiquement. `gh pr merge --squash --auto` merge dès que les checks passent.

Pas de relecture obligatoire (dépôt mono-utilisateur : on ne peut pas approuver sa propre PR). Le garde-fou, ce sont les checks et le template.

## Ce qui est imposé (rulesets)

| Cible | Règles |
|---|---|
| `main` et `release/**` | PR obligatoire · squash seul · historique linéaire · checks `CI ok` + `Titre de PR` exigés (sans obligation d'être à jour avec `main`) · conversations résolues · pas de force-push ni de suppression · aucun contournement |
| tags `v*` | ni suppression ni déplacement : une version publiée est immuable |

`CI ok` est un job agrégé de `ci.yml` : c'est lui seul qui est exigé, la liste des jobs peut donc évoluer sans toucher aux règles. Modifier une règle : éditer le JSON dans `.github/rulesets/`, passer par une PR, puis relancer `scripts/github_rules.sh` (admin).

En cas d'urgence absolue (CI cassé par GitHub lui-même), désactiver temporairement le ruleset dans Réglages → Rules, merger, **le réactiver**, et le dire dans la PR.

## Releases et branches `release/X.Y`

Cas courant : on tague `main` (`make release V=X.Y.Z`, skill `numera-release`). Pas de branche de release permanente : une seule version est supportée (la dernière), elle coûterait des cherry-picks pour rien.

Une branche `release/X.Y` ne se crée **qu'à la demande**, quand `main` a déjà avancé avec des changements qu'on ne veut pas livrer et qu'une version publiée a besoin d'un correctif :

```bash
git switch -c release/0.2 v0.2.0 && git push -u origin release/0.2
```

Le correctif se fait d'abord sur `main` (PR normale), puis se rétro-porte par une PR vers `release/0.2` (`git cherry-pick -x <sha>`), le titre commençant par `fix(...)`. Une fois mergée, `make release V=0.2.1` depuis `release/0.2` (le workflow `release.yml` accepte un tag présent sur `main` ou sur `release/*`). La branche est protégée comme `main`. (Non éprouvé : si le ruleset refuse la création de la branche par `git push`, la créer via `gh api repos/Hugo-Galley/numera/git/refs` ou désactiver brièvement le ruleset `release/*`, puis corriger cette page.)

## Dependabot

Les PRs Dependabot (préfixe `build(deps)`) suivent le même chemin : checks verts, squash. Une montée de version majeure se lit avant de merger.

## Pourquoi la branche n'a pas à être à jour avec `main`

Exiger « à jour » (mode strict) force un rebase puis une CI complète (4 à 6 min) sur toutes les PR ouvertes après chaque merge : avec 4 PR, 4 cycles à la suite. La merge queue de GitHub, qui règle ce problème, n'existe pas pour un dépôt de compte personnel. Le coût accepté : une PR est testée sur sa base, pas sur le résultat exact du merge, donc deux PR vertes qui se contredisent sémantiquement (sans conflit de texte) peuvent casser `main`. Le filet : la CI tourne aussi à chaque push sur `main` (`ci.yml`), et un `main` rouge se corrige tout de suite par une PR. Si ça arrive plus d'une fois, revenir au mode strict (remettre `true` dans `.github/rulesets/*.json` et relancer `scripts/github_rules.sh`).
