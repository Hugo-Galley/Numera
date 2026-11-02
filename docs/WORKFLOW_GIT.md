# Workflow Git : PR obligatoire

`main` est protégée : plus aucun push direct, tout passe par une pull request dont les checks sont verts. Les règles sont versionnées (`.github/rulesets/`) et appliquées par `scripts/github_rules.sh`.

## Cycle d'un changement

1. **Partir de `main` à jour**, créer une branche : `type/sujet-court` (`feat/export-pdf`, `fix/solde-courant`, `docs/workflow-git`). Un sujet par branche.
2. **Commiter** comme avant (Conventional Commits, corps = pourquoi). Les commits de la branche sont libres : seul le titre de la PR compte (squash).
3. **Valider en local** : `make validate` (skill `numera-finishing`). Une fois par clone, `make hooks` installe les garde-fous git (`.pre-commit-config.yaml`) : au commit gitleaks (secrets), ruff et plafonds de taille, au push mypy et typecheck frontend. Ils rejouent des contrôles de la CI plus tôt, ils ne les remplacent pas ; `make pre-commit-all` les lance sur tout le dépôt.
4. **Pousser et ouvrir la PR** : `gh pr create --fill-first` puis compléter le template. Le **titre** respecte `type(portée): description` (check « Titre de PR »), car il devient le commit sur `main` et la ligne des notes de version. Changement incompatible : `!` avant `:` (`feat(api)!: …`).
5. **Attendre les checks** : `CI ok` (backend, frontend, e2e, hadolint, Trivy repo et images) et `Titre de PR`. La branche doit être à jour avec `main` (bouton « Update branch » ou `git rebase origin/main`), les conversations résolues.
6. **Merger en squash** (seule méthode autorisée). La branche est supprimée automatiquement. `gh pr merge --squash --auto` merge dès que les checks passent.

Pas de relecture obligatoire (dépôt mono-utilisateur : on ne peut pas approuver sa propre PR). Le garde-fou, ce sont les checks et le template.

## Ce qui est imposé (rulesets)

| Cible | Règles |
|---|---|
| `main` et `release/**` | PR obligatoire · squash seul · historique linéaire · checks `CI ok` + `Titre de PR` exigés, branche à jour · conversations résolues · pas de force-push ni de suppression · aucun contournement |
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
