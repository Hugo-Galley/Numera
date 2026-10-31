---
name: numera-release
description: Use when deciding whether Numera should be released, choosing patch/minor/major, tagging a version, or when the user says "release", "publie", "nouvelle version". Also at the end of a work session that landed user-visible changes on main.
---

# Numera — releases

## Principe

Une release = un tag `vX.Y.Z` sur `main`. Le tag déclenche `.github/workflows/release.yml` : contrôle (commit sur `main`, CI vert) → 3 images multi-arch sur GHCR (`numera-backend`, `numera-frontend`, `numera-mcp`, tags `X.Y.Z`, `X.Y`, `latest`) → GitHub Release avec notes générées par `scripts/release_notes.py` depuis les commits Conventional Commits. Aucun changelog écrit à la main ; la qualité des notes dépend donc de celle des messages de commit (`type(portée): description`, le corps explique le pourquoi).

Le workflow joint à la Release un `docker-compose.yml` autonome (dérivé de `docker-compose.images.yml`, version de la release en défaut de `NUMERA_VERSION`). `install.sh` (mode « Docker », recommandé dans le README) le télécharge ; `docker-compose.images.yml` doit rester identique à `docker-compose.prod.yml` hors `build`/`image`/volumes (`tests/garde_fous/test_compose_images.py`). Toute modification de `docker-compose.prod.yml` se répercute donc dans `docker-compose.images.yml`.

## Autonomie

Je décide **seul** de proposer et de poser une release quand les critères ci-dessous sont réunis, sans attendre que l'utilisateur le demande. L'utilisateur peut aussi la demander explicitement (« release », « sors une 0.4 ») : sa version ou son bump l'emporte alors sur le calcul. Il peut aussi dire de ne pas releaser : dans ce cas ne rien taguer.

Pousser un tag publie des images et une release publiques, c'est irréversible côté consommateurs : ne jamais **supprimer ni déplacer** un tag publié. Une erreur se corrige par une version suivante.

## Quand releaser

Releaser si, depuis le dernier tag, `python3 scripts/release_notes.py --bump` ne répond pas `none` **et** :

- l'ensemble des changements forme un état stable et validé (`make validate` vert sur `main`, CI vert) ;
- le dernier tag a plus de quelques commits `fix` / `feat` d'écart, **ou** un `fix` corrige un bug de données ou de sécurité (release immédiate, sans attendre le lot) ;
- aucun travail à moitié fini n'est sur `main` (fonction derrière un drapeau, migration à compléter).

Ne pas releaser : seulement `docs` / `test` / `chore` / `refactor` (le script répond `none`), CI rouge, changement en cours de session non validé, ou moins d'un jour après la précédente release sans correctif critique.

## Quel bump

Tant que la version majeure est `0` (état actuel, pas de tag avant la première release), les règles sont les mêmes mais on ne passe **pas** à `1.0.0` sans accord explicite de l'utilisateur (c'est un engagement de stabilité).

| Bump | Quand | Exemples |
|---|---|---|
| **patch** | corrections et perfs, rien de nouveau pour l'utilisateur | `fix(...)`, `perf(...)` |
| **minor** | nouvelle fonctionnalité visible, nouvelle route/page/réglage, migration additive | `feat(...)` |
| **major** | rupture : `type!:` ou `BREAKING CHANGE:` — route supprimée/renommée, variable d'environnement obligatoire nouvelle ou renommée, format d'export/import ou de sauvegarde incompatible, migration destructive ou non rejouable, changement du `docker-compose` demandant une action de l'utilisateur | |

`release_notes.py --bump` applique ces règles aux commits. Le relire avec jugement : un `feat` qui change un comportement existant de façon incompatible est un **major** même sans `!`. Dans ce cas, corriger la décision à la main et le dire dans le compte rendu (ne pas réécrire l'historique).

## Procédure

1. `git status` propre, sur `main`, à jour avec `origin/main` ; `git fetch --tags`.
2. `make validate` vert (sinon pas de release).
3. `make release-check` : bump suggéré, version suivante, aperçu des notes. Décider selon les sections ci-dessus.
4. `make release V=X.Y.Z` : vérifie (propre, sur `main`, tag libre, version > dernier tag), crée un tag annoté et le pousse.
5. Suivre le workflow (`gh run watch`), vérifier que la Release existe, qu'elle porte `docker-compose.yml` en pièce jointe, et que `docker pull ghcr.io/hugo-galley/numera-backend:X.Y.Z` fonctionne ; au premier tag, rendre les 3 paquets GHCR **publics** (Réglages du paquet → Change visibility), sinon `docker pull` demande une authentification.
6. Compte rendu à l'utilisateur : version, bump choisi et pourquoi, lien de la release, ce qui n'a pas été vérifié.

## Si le workflow échoue

- `verify` : le CI n'est pas vert sur le commit taggé → corriger sur `main`, puis **nouveau tag** (patch suivant). Ne pas forcer.
- `images` ou `release` en échec transitoire : relancer le job (`gh run rerun --failed`), sans toucher au tag.
