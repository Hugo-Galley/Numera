# ROADMAP.md

## Vision
Application locale de finance personnelle qui remplace un tableur Numbers et ajoute des vues plus fiables : budget, patrimoine, investissements, objectifs, comparaison, alertes et sauvegarde.

## État Global
- **Fonctionnalités Complétées** : L'application intègre la gestion des comptes (avec bannière de vérification périodique `last_verified_at` et compte principal `is_main`), l'import/export CSV (compatible Numbers), le multi-devise, le suivi budgétaire, les graphiques analytiques (organisés par onglets sur le Dashboard), le diagramme Sankey, le simulateur de patrimoine, les abonnements, les alertes, les tags personnalisés, la normalisation des marchands (avec synonymes/alias), les transactions récurrentes, le Centre d'Actions (avec diagnostic et résolutions de l'audit de données), le système de gestion de salaire (avec suivi du télétravail TT et tickets restaurant TR), et les sauvegardes automatisées avec chiffrement Fernet.
- **Prochains Objectifs** : Projeter le budget de fin de mois (Priorité 1), permettre le drill-down interactif depuis les graphiques (Priorité 2), et fiabiliser la validation technique (tests unitaires et E2E sur le frontend).

---

## Plan de Développement Priorisé

### 1. Budget Prévisionnel de Fin de Mois
*Estimer le reste à vivre et anticiper les risques de dépassement avant la fin du mois.*
- **Objectifs** :
  - Projection des dépenses d'ici la fin du mois basée sur le rythme courant de consommation.
  - Prise en compte des transactions récurrentes restantes sur la période.
  - Estimation dynamique du solde prévisionnel de fin de mois.
  - Alertes préventives de dépassement par catégorie budgétaire.
  - Affichage des projections sur le dashboard et le calendrier financier.

### 2. Drill-Down Interactif depuis les Graphiques
*Rendre les représentations visuelles actionnables.*
- **Objectifs** :
  - Clic sur une catégorie/marchand -> redirection vers la liste des transactions filtrées.
  - Clic sur un mois -> ouverture du rapport mensuel détaillé ou de la liste correspondante.
  - Clic sur un compte -> redirection vers le détail du compte.
  - Persistance des filtres appliqués dans l'URL pour un retour arrière aisé.

---

## Backlog Priorisé

### P1 - Fonctionnalités Produit

#### Grosses Dépenses Annuelles
*Lisser mentalement les dépenses lourdes mais peu fréquentes (impôts, assurances, vacances).*
- **Comportement attendu** :
  - Déclaration d'une dépense annuelle/ponctuelle avec date cible.
  - Calcul de la provision mensuelle théorique requise.
  - Suivi de la constitution de la provision et alertes en cas de retard.
  - Liaison optionnelle à un objectif d'épargne ou une transaction récurrente.
- **Notes d'implémentation** :
  - Peut démarrer comme un type de récurrence annuelle enrichie.
  - Ne pas insérer de fausses transactions dans l'historique réel (distinguer le prévisionnel du réel).

#### Saisie Ultra-Rapide depuis l'Omnibox
*Ajouter des transactions en langage naturel rapidement depuis la barre de recherche globale.*
- **Comportement attendu** :
  - Parsing de commandes simples (ex: `sortie 12.50 kfc nourriture` ou `entree 120 maman remboursement`).
  - Aperçu de la transaction interprétée avant confirmation de création.
  - Utilisation du compte par défaut, application des règles d'auto-catégorisation, gestion des tags/devises si spécifiés.
- **Notes d'implémentation** :
  - Grammaire de parsing simple et robuste. Aucune transaction ne doit être créée sans confirmation claire de l'utilisateur.

#### Import Bancaire Flexible
*Faciliter l'importation de fichiers CSV de différentes banques sans reconfiguration manuelle.*
- **Comportement attendu** :
  - Sauvegarde et gestion de profils de mapping personnalisés par banque.
  - Détection automatique du profil d'import basé sur la structure du fichier CSV.
  - Visualisation des transactions avant l'importation définitive.
  - Application des règles locales d'auto-catégorisation et de normalisation des marchands post-import.
- **Notes d'implémentation** :
  - Étendre le pipeline existant sans altérer le support du format CSV de Numbers. Maintenir l'idempotence.

#### Archivage Intelligent
*Masquer les éléments obsolètes ou peu utilisés pour réduire le bruit visuel.*
- **Comportement attendu** :
  - Archivage des comptes fermés, catégories obsolètes, marchands ou tags inutilisés.
  - Masquage par défaut dans les filtres, formulaires et graphiques (avec historique préservé).
  - Suggestions automatiques d'archivage basées sur l'inactivité.
- **Notes d'implémentation** :
  - Ajout d'un indicateur d'activation (`active` ou `archived_at`) sur les modèles concernés.

### P2 - Visualisations & UX

#### Allocation Cible de Patrimoine
- Comparaison entre l'allocation cible définie par classe d'actifs, secteur ou zone géographique et l'allocation réelle actuelle.
- Suggestion d'orientation pour le prochain versement d'investissement afin de rééquilibrer le portefeuille.

#### Historique des Décisions Financières
*Conserver le contexte des événements marquants sur les graphiques temporels.*
- **Comportement attendu** :
  - Ajout de notes datées (ex: résiliation d'abonnement, hausse d'épargne, achat immobilier, changement d'allocation).
  - Affichage contextuel de ces jalons sur les courbes de patrimoine ou d'évolution budgétaire.
- **Notes d'implémentation** :
  - Modélisation simple (`financial_events` ou `decision_notes`) reliée optionnellement à un compte/catégorie/objectif.

#### Templates de Catégories
*Faciliter la configuration ou la restructuration des catégories de dépenses.*
- **Comportement attendu** :
  - Proposition de modèles prédéfinis (Étudiant, Famille, Investisseur, Minimaliste).
  - Importation sans écrasement des catégories existantes.
- **Notes d'implémentation** :
  - Stockage des structures types dans le backend ou fichier de configuration.

#### Drill-down sur l'Allocation d'Actifs
- Exploration interactive de la répartition du patrimoine par classe d'actifs, zone géographique ou secteur.

### P3 - Améliorations Techniques

#### Automatisation & Qualité Frontend
- Intégration de runners de tests frontend et de scripts pour le linting/typechecking (`lint`, `typecheck`, `test`) dans le fichier [package.json](file:///Users/hugogalley/DEV/numera/frontend/package.json) et le [Makefile](file:///Users/hugogalley/DEV/numera/Makefile).

#### Gestion des Secrets & Configuration
- Clarifier et standardiser la politique de secrets dev/prod et de variables d'environnement.

#### Contraintes d'Intégrité de la Base de Données
- Ajout de migrations de base de données pour renforcer les contraintes d'unicité métier et éviter d'éventuels doublons orphelins.

---

## Critères de Livraison Généraux
- Les calculs financiers sensibles s'effectuent côté backend.
- Aucune modification destructive sans migration de base de données.
- Imports idempotents et rejouables sans doublons.
- Les tests du backend doivent tous réussir (`make validate` ou pytest).
- Le build frontend en production doit réussir sans erreur de typage TypeScript.
