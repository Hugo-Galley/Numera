# ROADMAP.md

## Vision

Application locale de finance personnelle qui remplace un tableur Numbers et ajoute des vues plus fiables: budget, patrimoine, investissements, objectifs, comparaison, alertes et sauvegarde.

## Etat Global

- MVP budget/import/export: terminé.
- Visualisations et pages métier: terminé.
- UX avancée, multi-devise, objectifs, alertes, backups, abonnements, règles de catégorisation, tags, calendrier financier, rapports mensuels, Sankey et simulation de patrimoine : entièrement implémentés.
- Prochain travail utile: stabilisation, tests frontend, mode audit des données, normalisation des marchands, et ergonomie.

## Termine

### Sprint 1 - Fondation, donnees, import, budget

- Socle Docker, backend FastAPI, frontend React/Vite.
- SQLite + SQLAlchemy + Alembic.
- CRUD comptes, catégories, transactions.
- Import CSV Numbers avec preview, normalisation et déduplication.
- Dashboard budget v1.

### Sprint 2 - Visualisations, pages métier, export

- Graphiques dépenses par catégorie, top marchands, timeseries, entrées/sorties.
- Pages comptes et détail compte avec transactions filtrables.
- Pages investissements avec flux, snapshots, performance, point zéro.
- Export CSV compatible Numbers.
- Tests backend critiques import, analytics, export, investissements.

### Sprint 3 - UX et analyse avancée

- Mode confidentialité UI.
- Vue comparaison mensuelle.
- Multi-devise avec taux courants et historiques.
- Recherche transactionnelle et marchands.

### Sprint 4 - Sécurité, analytics avancés & fonctionnalités produit (Juin 2026)

- Authentification mono-admin JWT et routes protégées. [OK]
- Sidecar de sauvegarde Docker avec chiffrement optionnel (Fernet). [OK]
- Objectifs d'épargne enrichis par mot-clé (date cible, montant mensuel recommandé, lien compte/catégorie). [OK]
- Omnibox globale pour navigation et actions. [OK]
- Allocation avancée par classe d'actifs, secteur et zone géographique. [OK]
- Alertes budget par limites de catégories et détection d'insights/anomalies. [OK]
- Mise à jour en masse (bulk update) des transactions. [OK]
- Système de logging amélioré dans `backend/LOGGING.md`. [OK]
- Calendrier financier mensuel avec projections de solde et de cashflow. [OK]
- Transactions récurrentes complètes (gestion, génération automatique et validation). [OK]
- Bilan mensuel intelligent avec résumé automatique et exportation PDF pro. [OK]
- Détection et rapprochement automatique des transferts internes entre comptes. [OK]
- Tags personnalisables pour suivre des projets ou contextes transverses. [OK]
- Auto-catégorisation par règles locales de marchand. [OK]
- Vue dédiée aux abonnements et charges fixes (coût mensuel/annuel, détection des nouveaux). [OK]
- Filtrage multicritères complet sur toutes les listes. [OK]
- Fonds de sécurité (mois de dépenses couverts par cash/épargne liquide) et Score de santé financière. [OK]
- Diagramme Sankey des flux (revenus vers dépenses, épargne, investissements). [OK]
- Simulateur de patrimoine dynamique avec hypothèses de rendement et versements. [OK]
- Vue diagnostic "Où est passé mon argent ?" dans le rapport mensuel. [OK]
- Routine de validation complète dans le `Makefile` (`make validate` incluant tests + build frontend). [OK]
- Procédure de restauration de backup validée et scriptée (`make backup-restore`). [OK]
- Tests unitaires et d'intégration robustes couvrant toutes ces fonctionnalités (39 tests au total). [OK]


## En Cours Ou Partiel

- Frontend tests: aucun runner de test frontend configuré, seulement le build Vite en vérification.
- Lint/format: pas de scripts dédiés dans `package.json` ou `Makefile`.

## Plan De Dev Priorise

Objectif: developper les ameliorations produit une par une, en gardant les calculs sensibles cote backend et des actions explicites cote UI.

### Priorite 1 - Mode Audit Des Donnees

Statut: en cours.

Objectif: renforcer la confiance dans les chiffres avant d'ajouter de nouveaux automatismes.

Livrable v1:

- Endpoint `/analytics/audit`.
- Page dediee "Audit des donnees".
- Detection des transactions sans categorie.
- Detection des doublons suspects.
- Detection des marchands manquants.
- Detection des comptes actifs sans solde initial.
- Detection des comptes investissement sans snapshot recent.
- Detection des categories inutilisees.
- Detection des transferts internes possibles.
- Actions de navigation vers les ecrans de correction existants.

Extensions futures:

- Corrections en un clic quand les APIs existantes le permettent.
- Filtres par severite et type d'alerte.
- Ignorer une alerte connue sans modifier les donnees sources.
- Historique du score de proprete.

### Priorite 2 - Centre D'Actions

Objectif: transformer les insights en file d'actions concrete.

- Categoriser les transactions restantes.
- Creer une regle depuis un marchand recurrent.
- Confirmer des abonnements detectes.
- Mettre a jour les snapshots d'investissement.
- Rapprocher les transferts internes.
- Signaler les budgets depasses ou a risque.

### Priorite 3 - Normalisation Des Marchands

Objectif: regrouper les variantes de libelles bancaires sous un marchand canonique.

- Table de marchands canoniques ou synonymes.
- Conservation du libelle original.
- Suggestions automatiques sur libelles proches.
- Correction et dissociation manuelles.
- Utilisation dans graphiques, filtres, imports et regles.

### Priorite 4 - Budget Previsionnel De Fin De Mois

Objectif: estimer le reste a vivre et les risques avant la fin du mois.

- Projection depuis le rythme courant.
- Ajout des recurrentes restantes.
- Estimation du solde de fin de mois.
- Risque de depassement par categorie.
- Affichage sur dashboard et calendrier.

### Priorite 5 - Drill-Down Depuis Les Graphiques

Objectif: rendre chaque graphe actionnable.

- Clic categorie -> transactions filtrees.
- Clic marchand -> transactions filtrees.
- Clic mois -> rapport ou liste filtree.
- Clic compte -> detail compte.
- Conservation des filtres dans l'URL.

## Backlog Priorise

### P0 - Fiabilite

- Mode audit des données: doublons suspects, transactions sans catégorie, solde initial absent, snapshots manquants et catégories inutilisées.

### P1 - Produit

- Normalisation des marchands avec libellé canonique et conservation du libellé original.
- Grosses dépenses annuelles: provision mensuelle théorique et rappels.
- Saisie ultra-rapide de transactions depuis l'omnibox.
- Import bancaire flexible avec profils de mapping sauvegardés par banque.
- Archivage intelligent des comptes, catégories et marchands peu utilisés.

### P2 - Visualisations

- Allocation cible de patrimoine avec comparaison à l'allocation réelle et suggestion d'orientation du prochain versement.
- Historique des décisions financières pour contextualiser les courbes.
- Templates de catégories pour initialiser ou réorganiser rapidement le suivi.
- Drill-down interactif sur l'allocation par zone/secteur/asset class.

### P3 - Technique

- Ajouter scripts `lint`, `typecheck`, `test` frontend.
- Clarifier la politique de secrets dev/prod.
- Ajouter migrations/tests pour contraintes d'unicité métier supplémentaires.

## Criteres De Livraison Generaux

- Les calculs finance restent cote backend.
- Les donnees existantes ne sont pas migrees destructivement.
- Les imports sont re-jouables sans duplication.
- Les tests backend critiques passent.
- Les pages modifiees buildent en TypeScript.

## Idees Produit Retenues

Ces idees sont retenues comme extensions naturelles du produit. Elles doivent garder la philosophie locale, personnelle et fiable de l'application: les donnees restent sous controle utilisateur, les calculs financiers sensibles restent cote backend, et les automatismes doivent toujours etre explicites ou desactivables.

### 12. Normalisation Des Marchands

Objectif: regrouper les variantes de libelles bancaires sous un marchand canonique pour rendre les graphiques plus propres.

Comportement attendu:

- Associer plusieurs libelles originaux a un marchand canonique.
- Afficher le marchand canonique dans les graphes et filtres principaux.
- Conserver le libelle original de la transaction pour l'audit.
- Proposer des regroupements automatiques sur les libelles proches.
- Permettre de corriger ou dissocier un regroupement.

Notes d'implementation:

- Ajouter une table de marchands ou de synonymes de marchands.
- Garder la compatibilite avec le champ `merchant` existant.
- Faire attention aux prenoms et remboursements personnels, qui peuvent etre des marchands utiles dans le modele actuel.
- Ajouter des tests sur casse, accents, espaces, prefixes bancaires et collision entre deux marchands.

### 13. Tags Personnalises

Objectif: suivre des projets ou contextes transverses sans multiplier les categories.

Comportement attendu:

- Ajouter un ou plusieurs tags a une transaction.
- Filtrer les listes et analytics par tag.
- Creer des tags pour vacances, travaux, sante, cadeaux, projet perso ou evenement ponctuel.
- Afficher un total par tag sur une periode.
- Permettre une application en masse depuis les transactions filtrees.

Notes d'implementation:

- Ajouter des tables `tags` et `transaction_tags`.
- Ne pas remplacer les categories: un tag est transversal, une categorie reste le poste budgetaire principal.
- Prevoir la prise en charge des exports si les tags deviennent importants.
- Tester suppression de tag, transaction multi-tags et filtres combines categorie + tag.

### 14. Vue "Ou Est Passe Mon Argent ?"

Objectif: expliquer un mois en langage simple avec une decomposition claire des flux.

Comportement attendu:

- Partir des revenus du mois.
- Soustraire charges fixes, depenses variables, epargne et investissements.
- Afficher le reste final et les principaux postes explicatifs.
- Montrer les ecarts avec le mois precedent.
- Donner une lecture plus diagnostic que graphique.

Notes d'implementation:

- S'appuyer sur les categories, abonnements, recurrentes et transferts internes.
- Garder les calculs cote backend pour eviter les divergences de KPI.
- Reutiliser cette logique dans le bilan mensuel intelligent si possible.

### 15. Score De Sante Financiere

Objectif: fournir un signal synthetique sur l'etat financier du moment sans remplacer le detail des KPI.

Comportement attendu:

- Calculer un score base sur taux d'epargne, burn rate, regularite des depenses, fonds de securite et progression des objectifs.
- Afficher les sous-scores pour expliquer la note.
- Montrer les leviers d'amelioration.
- Eviter les formulations anxiogenes ou culpabilisantes.
- Permettre d'ignorer certains criteres si non pertinents.

Notes d'implementation:

- Rendre la formule explicite dans la doc ou dans l'interface.
- Ne pas melanger ce score avec du conseil financier personnalise.
- Tester les cas sans revenus, sans objectifs, mois partiel et donnees historiques faibles.

### 16. Fonds De Securite

Objectif: estimer combien de mois de depenses peuvent etre couverts par le cash et l'epargne disponible.

Comportement attendu:

- Calculer les depenses reelles moyennes sur une periode recente.
- Additionner les comptes consideres comme disponibles: courant et epargne liquide.
- Afficher un nombre de mois de securite.
- Permettre d'exclure certains comptes du calcul.
- Relier ce calcul a un objectif d'epargne si l'utilisateur le souhaite.

Notes d'implementation:

- Distinguer cash disponible, epargne liquide et investissements long terme.
- Exclure les transferts internes et investissements des depenses reelles.
- Ajouter des tests sur compte epargne sans snapshot, mois sans donnees et variation forte de depenses.

### 17. Grosses Depenses Annuelles

Objectif: anticiper les depenses rares mais lourdes en les lissant mentalement sur l'annee.

Comportement attendu:

- Declarer une depense annuelle ou ponctuelle: impots, assurance, vacances, entretien, cadeaux.
- Calculer la provision mensuelle theorique.
- Afficher les prochaines echeances.
- Signaler si la provision est en retard.
- Permettre de lier une depense annuelle a un objectif ou une recurrence.

Notes d'implementation:

- Peut demarrer comme un type de recurrence annuelle enrichie.
- Ne pas inserer automatiquement de fausse depense mensuelle dans l'historique.
- Distinguer budget previsionnel et transaction reelle.

### 18. Historique Des Decisions Financieres

Objectif: garder le contexte des changements qui expliquent les courbes.

Comportement attendu:

- Ajouter une note datee: abonnement resilie, hausse d'epargne, achat important, changement d'allocation.
- Afficher ces notes sur les bilans ou graphiques temporels.
- Filtrer par type de decision.
- Lier une decision a un compte, une categorie, un objectif ou une transaction.

Notes d'implementation:

- Ajouter une table simple `financial_events` ou `decision_notes`.
- Garder cette fonctionnalite optionnelle et peu intrusive.
- Prevoir une restitution dans le bilan mensuel et les courbes de patrimoine.

### 19. Saisie Ultra-Rapide Depuis L'Omnibox

Objectif: ajouter une transaction en quelques mots, sans ouvrir un formulaire complet.

Comportement attendu:

- Parser des commandes comme `sortie 12.50 kfc nourriture` ou `entree 120 maman remboursement`.
- Proposer une preview avant creation.
- Utiliser le compte courant par defaut si aucun compte n'est indique.
- Appliquer les regles d'auto-categorisation quand elles existent.
- Gerer date, note, devise et tag si presents dans la commande.

Notes d'implementation:

- Commencer avec une grammaire simple et robuste.
- Ne creer aucune transaction sans confirmation claire.
- Ajouter des tests sur formats de montant francais/anglais, categories absentes et commande incomplete.

### 20. Import Bancaire Flexible

Objectif: importer des CSV de banques differentes sans recreer le mapping a chaque fois.

Comportement attendu:

- Sauvegarder un profil de mapping par banque ou type de fichier.
- Mapper date, montant, libelle, debit, credit, devise et solde si disponibles.
- Detecter automatiquement un profil compatible.
- Montrer un apercu avant import.
- Reutiliser les regles d'auto-categorisation et normalisation marchands apres import.

Notes d'implementation:

- Etendre le pipeline d'import existant sans casser le format Numbers.
- Garder l'idempotence sur les transactions importees.
- Ajouter des tests par format de banque des qu'un profil est ajoute.

### 21. Templates De Categories

Objectif: faciliter l'initialisation ou la reorganisation des categories.

Comportement attendu:

- Proposer des ensembles predefinis: salarie, etudiant, investisseur, minimaliste.
- Permettre d'importer un template sans supprimer les categories existantes.
- Afficher les categories qui seraient creees ou ignorees.
- Garder les limites de budget optionnelles dans les templates.

Notes d'implementation:

- Stocker les templates dans le backend ou dans un fichier de seed versionne.
- Ne jamais renommer ou fusionner automatiquement des categories existantes.
- Prevoir une action explicite pour appliquer un template.

### 22. Archivage Intelligent

Objectif: reduire le bruit dans les filtres et listes sans perdre l'historique.

Comportement attendu:

- Archiver des comptes, categories, marchands ou tags peu utilises.
- Masquer les elements archives par defaut dans les filtres.
- Garder les donnees historiques intactes.
- Proposer des elements a archiver selon l'inactivite.
- Permettre de restaurer un element archive.

Notes d'implementation:

- Ajouter des champs `active` ou `archived_at` selon les entites.
- Ne pas archiver automatiquement sans validation utilisateur.
- Tester les filtres, exports et analytics avec elements archives.

### 23. Mode Audit Des Donnees

Objectif: renforcer la confiance dans les chiffres en detectant les incoherences de donnees.

Comportement attendu:

- Detecter les doublons suspects.
- Lister les transactions sans categorie ou sans marchand.
- Signaler les comptes sans `Solde Initial` quand cela pose probleme.
- Signaler les comptes investissement sans snapshot recent.
- Identifier les categories, marchands ou tags inutilises.
- Proposer des actions correctives sans modifier automatiquement les donnees.

Notes d'implementation:

- Ajouter un endpoint d'audit dedie ou une page settings/audit.
- Prioriser les alertes qui peuvent fausser les KPI.
- Les corrections doivent passer par les APIs existantes quand c'est possible.
- Ajouter des tests sur chaque regle d'audit critique.
