<!--
Le TITRE de la PR devient le message du commit (merge en squash) et alimente les notes de version.
Format obligatoire : type(portée): description   ex. fix(budget): arrondi du solde courant
Types : feat fix perf refactor test docs build ci chore revert style · `!` avant `:` = changement incompatible
-->

## Pourquoi

<!-- Le problème ou le besoin, pas la liste des fichiers modifiés. Lien vers l'issue : « Closes #123 ». -->

## Ce qui change

<!-- Comportement visible, décisions de conception, alternatives écartées. -->

## Zones touchées

- [ ] Backend
- [ ] Frontend
- [ ] Migration Alembic
- [ ] Docker / CI / workflows
- [ ] Docs / skills uniquement

## Vérification

<!-- Ce qui a été lancé et son résultat (commande + sortie utile). Ce qui n'a PAS été vérifié, dit franchement. -->

- [ ] `make validate` vert en local
- [ ] Test rouge écrit avant le code (backend, skill `numera-tdd`)
- [ ] Rendu vérifié à la main : clair/sombre, mobile, mode confidentialité (si UI)

## Check-list

- [ ] `ARCHITECTURE.md`, `CLAUDE.md` ou le skill concerné mis à jour (route, modèle, commande, règle métier)
- [ ] Aucun seuil à cliquet baissé (couverture, tailles, ESLint) ni baseline augmentée
- [ ] Aucun tag flottant : actions épinglées par SHA, images par digest
- [ ] Migration réversible et testée sur une base existante (si schéma modifié)
- [ ] Mesures avant/après dans cette description (si optimisation, skill `numera-performance`)
- [ ] Un seul sujet : pas de refactor mélangé à un changement de comportement

## Risques et retour arrière

<!-- Migration irréversible, changement de format de données, variable d'environnement nouvelle ? Sinon « aucun ». -->
