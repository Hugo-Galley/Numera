# Revue de mois : vérification des comptes par rapprochement

## Pourquoi

L'étape « Comptes » de la revue de mois est pénible. Elle affiche le solde d'aujourd'hui, alors que le relevé s'arrête à la fin du mois. Elle ne propose qu'un bouton « Valider », sans saisie du solde de la banque, donc sans écart affiché ni aide pour corriger. Les trois difficultés : retrouver le bon chiffre, comprendre l'écart, le corriger.

## Approches envisagées

- **A. Rapprochement directement dans la liste** : un champ « solde du relevé » par compte, et l'écart avec ses causes probables affichés juste en dessous. **Retenue.**
- **B. Ouvrir la fenêtre `ReconcileDialog` existante** : rapide à faire, mais une fenêtre par compte reste lourd. Écartée.
- **C. Tri automatique** : les comptes qui n'ont pas bougé sont validés en un clic. **Retenue, en complément de A.**

## Objectifs

1. Afficher le solde de Numera **à la date du relevé**, et non aujourd'hui.
2. Pour chaque compte bancaire, un champ « solde du relevé ». S'il colle, le compte est validé automatiquement. Sinon, afficher l'écart et les causes probables : doublon, ligne en trop ou manquante, signe inversé, transaction manquante.
3. Regrouper les comptes sans aucune transaction depuis leur dernière vérification dans un bloc « Rien n'a bougé », validable en un clic.
4. Traiter les placements (`investissement`, `assurance_vie`) à part : valeur actuelle et simple bouton « Valider ».

## Non-objectifs

- Aucune correction automatique : un doublon détecté n'est jamais supprimé sans que l'utilisateur le décide.
- Pas de rapprochement des placements par valeur de marché.
- Pas d'import de relevé (CSV, PDF) dans cette étape.

## Anti-objectifs

L'étape ne doit pas demander plus de clics qu'aujourd'hui pour un mois sans surprise.

## Conception

### Backend (`services/budget/month_review.py::_accounts_step`)

Champs ajoutés pour chaque compte :
- `group` : `reconcile` (compte bancaire qui a bougé), `unchanged` (compte bancaire sans transaction datée entre `last_verified_at` et la date du relevé) ou `market` (placements).
- `statement_date` : dernier jour **calendaire** du mois revu, plafonné à aujourd'hui.
- `statement_balance` : `reconciliation.balance_at(account, statement_date)` pour les comptes bancaires.
- `balance` reste la valeur actuelle, utilisée pour `market`.

Nouvelle route `POST /month-review/accounts/confirm-unchanged` (`{year, month}`) : elle marque vérifiés, en un seul commit, les comptes du groupe `unchanged`. Elle renvoie la revue mise à jour. Elle est ajoutée au router déjà protégé et documentée dans `ARCHITECTURE.md`.

Le rapprochement réutilise `POST /accounts/{id}/reconcile`, avec `date = statement_date`. Aucune logique n'est dupliquée.

### Frontend (`components/month-review/AccountsStep.tsx`)

Trois blocs, dans cet ordre :

```
À rapprocher (au 31/10)
  Compte courant   Numera : 1 248,30 €   [ relevé ______ ] [Vérifier]   ou   ✅ Validé
  Livret A         Numera : 5 400,00 €   [ 5 380,00 ]                       ⚠ écart −20,00 €
      ↳ Doublon probable : 12/10 · Netflix −20 €   [Voir la transaction]
      (lien secondaire « Valider sans saisir »)

Rien n'a bougé depuis la dernière vérification (3)
  PEL · Compte joint · Livret jeune                              [Tout valider]

Placements (valeur actuelle)
  PEA        12 430 €                                            [Valider]
```

- Le rendu d'une cause probable est extrait de `ReconcileDialog` dans un composant partagé, utilisé par la fenêtre et par la revue.
- La touche Entrée dans le champ lance la vérification. Après une vérification réussie, le focus passe au compte suivant.
- Les montants sont floutés en mode confidentialité (`amount-blur`).
- Textes traduits en fr, en et es.

## Contraintes

Méthode TDD côté backend (skill `numera-tdd`) et tests Vitest pour l'étape. Bornes de dates exclusives (`< end`). Garde-fous d'architecture et de taille de code. Mise à jour d'`ARCHITECTURE.md`. Aucun outil MCP, la route étant une écriture.

## Décisions laissées à l'implémentation (choix de Claude, à vérifier)

- La date du relevé est la fin du mois **calendaire**, même si le mois budgétaire suit la paie : c'est la date imprimée sur un relevé bancaire.
- « A bougé » est déterminé par la date des transactions, non par leur date de création : une transaction importée en retard mais datée d'avant la dernière vérification ne compte pas.
- Le lien « Voir la transaction » mène à la liste des transactions du compte, filtrée sur ce marchand.
