# Cahier des charges — Application de finance personnelle (self-hosted)
### Version 2.0 — Mis à jour depuis le tableur Numbers existant

---

## Note Pour Agents IA

Ce fichier est le cahier des charges produit historique. Pour l'etat reel du code, lire d'abord `AGENT.MD`, `README.md`, `ARCHITECTURE.md`, `ROADMAP.md` et `TEST_PLAN.md`.

Le depot actuel depasse le MVP decrit ici sur plusieurs points:

- Authentification mono-admin JWT.
- Multi-devise actif avec Frankfurter et cache de taux historiques.
- Objectifs d'epargne.
- Comparaison mensuelle.
- Omnibox et mode confidentialite.
- Alertes budget, insights et detection d'anomalies.
- Allocation d'actifs avancee.
- Sauvegardes chiffrees via sidecar Docker.

Les regles fonctionnelles de ce document restent valables quand elles ne contredisent pas l'etat reel documente dans `AGENT.MD` et `ARCHITECTURE.md`.

---

## 1. Contexte et objectifs

L'utilisateur souhaite remplacer un tableur Numbers par une application web moderne, hébergée localement (self-hosted). L'application est à usage strictement personnel (1 utilisateur, pas d'authentification multi-compte requise).

L'utilisateur possède déjà un historique de données dans Numbers qu'il doit pouvoir importer au démarrage.

**Objectifs principaux :**
- Reproduire et enrichir tous les KPI et graphiques du tableur Numbers existant
- Avoir une vision claire et centralisée de son patrimoine
- Suivre précisément ses comptes d'investissement (versements, retraits, valeur actuelle, performance)
- Suivre son compte courant avec catégorisation des dépenses par commerçant
- Permettre l'import des données historiques existantes

---

## 2. Périmètre des comptes

| Compte | Type | Suivi |
|---|---|---|
| Compte courant | Courant | Solde + transactions catégorisées + commerçants |
| Livret A (ou épargne réglementée) | Épargne | Versements / retraits + valeur actuelle |
| PEA | Investissement | Versements / retraits + valeur actuelle |
| Assurance-vie | Investissement | Versements / retraits + valeur actuelle |
| CTO (Compte-Titres Ordinaire) | Investissement | Versements / retraits + valeur actuelle |
| Crypto | Investissement | Versements / retraits + valeur actuelle |

> Le nombre exact de comptes peut varier entre 4 et 6. L'interface doit permettre d'en ajouter ou d'en archiver librement.

---

## 3. Modèle de données

### 3.1 Compte (Account)

```
id, nom, type (courant | épargne | investissement), devise (défaut: EUR),
date_création, actif (bool), couleur (pour différenciation visuelle)
```

### 3.2 Transaction du compte courant (Transaction)

Basé sur le référentiel Numbers existant :

```
id, account_id, date (datetime), mois (string, ex: "Janvier"),
type (Entré | Sortie | Solde Initial),
commerçant (string — nom du commerçant ou de la personne),
catégorie_id (nullable),
montant (€, toujours positif — le type Entré/Sortie indique le sens),
solde_compte (€, calculé automatiquement),
note (optionnel)
```

> **Important :** Le champ `commerçant` est central. Il peut contenir un nom de boutique (KFC, Intermarché), un abonnement (YouTube Premium, Navigo, Bouygue Telecom), ou un prénom (Denis, Nolan, Maman). C'est ce champ qui alimente les graphiques "Top Commerçants" et "Montant cumulé abonnements".

**Type "Solde Initial"** : ligne spéciale créée automatiquement lors de la création du compte courant, ou lors d'un reset de solde. Elle fixe le solde de départ sans être comptée comme une entrée ou sortie réelle dans les agrégats.

### 3.3 Catégorie (Category)

```
id, nom, icône, couleur, type (dépense | revenu | neutre)
```

**Catégories existantes dans le tableur (à pré-charger) :**

Dépenses : Abonnement, Achat divers, Nourriture, Sortie, Cadeaux (émis), Don, Sport, Catégorie (à renommer)
Revenus : Remboursement (reçu), Salaire, Revenus supplémentaires

### 3.4 Opération d'investissement (InvestmentTransaction)

```
id, account_id, date, type (versement | retrait), montant (€), note (optionnel)
```

### 3.5 Snapshot de valeur (BalanceSnapshot)

Pour les comptes d'investissement — permet de définir la valeur actuelle à une date donnée.

```
id, account_id, date, valeur_actuelle (€), note (optionnel), est_point_zero (bool)
```

---

## 4. Dashboard principal — Section "Budget"

### 4.1 Tableau Budget (colonne gauche)

Reproduire exactement la structure du tableur Numbers :

**Bloc Entrées d'argent (fond vert)**
| Ligne | Valeur |
|---|---|
| Salaire | montant mensuel |
| Revenus supplémentaires | montant mensuel |
| **Revenus totaux** | somme |

**Bloc Catégories de dépenses (fond rouge)**
| Catégorie | Montant (Somme) |
|---|---|
| Abonnement | total du mois |
| Achat divers | total du mois |
| Catégorie | total du mois |
| Investissement | total du mois |
| Nourriture | total du mois |
| Sortie | total du mois |
| **Total général** | somme |

**Bloc Argent restant (fond bleu)**
| Ligne | Valeur |
|---|---|
| Revenus après dépenses | Revenus totaux – Total général |

> Le filtre mois doit être global sur le dashboard (sélecteur de mois en haut de page).

### 4.2 KPI globaux supplémentaires (cartes)

| KPI | Description |
|---|---|
| **Patrimoine net total** | Somme des soldes actuels de tous les comptes |
| **Total investi** | Versements nets cumulés sur tous les comptes d'investissement |
| **Performance investissements** | (Valeur actuelle – Total investi) / Total investi × 100 |
| **Taux d'épargne mensuel** | Revenus après dépenses / Revenus totaux × 100 |
| **Burn Rate (€/jour)** | Moyenne quotidienne des dépenses du mois |

---

## 5. Dashboard — Section "Répartition de l'argent"

### 5.1 Graphiques donut

1. **Sorties d'argent** — répartition des dépenses par catégorie (% du total des sorties du mois)
2. **Abonnements** — répartition des abonnements par commerçant (Spotify, YouTube Premium, Navigo, Bouygue Telecom, Compte banque...) — filtré sur catégorie = "Abonnement"
3. **Répartition sortie totale** — toutes catégories confondues (Abonnement, Achat divers, Cadeaux, Don, Nourriture, Sortie, Sport...)

### 5.2 Graphiques barres horizontales

4. **Montant cumulé abonnement** — total annuel (ou depuis le début) par commerçant d'abonnement (Banque, Bouygue Telecom, Matmut, Navigo, Youtube Premium...)

---

## 6. Dashboard — Section "Top Dépenses"

| Graphique | Description |
|---|---|
| **Montant cumulé abonnement** | Barres horizontales, total par commerçant (catégorie Abonnement), sur la période sélectionnée |
| **Total dépense par catégories** | Barres verticales, total par catégorie, sur la période |
| **Top 5 Commerçants** | Barres horizontales, les 5 commerçants avec le plus gros total de dépenses |

---

## 7. Dashboard — Section "Dépenses dans le temps"

| Graphique | Description |
|---|---|
| **Évolution du compte courant** | Courbe du solde du compte courant dans le temps (par transaction) |
| **Total Entré / Sortie par mois** | Histogramme groupé : barres vertes (Total Dépense) + barres grises (Total Entré) par mois |
| **Évolution du salaire dans le temps** | Courbe du montant du salaire mois par mois |

---

## 8. Dashboard — Section "Investissement"

| Graphique | Description |
|---|---|
| **Répartition Investissement** | Donut : part de chaque compte d'investissement dans le total investi (PEA, Livret A, Cryptomonnaies, Assurance vie) |
| **Dépenses mensuelles par investissement** | Barres horizontales : versement du mois par compte d'investissement |

---

## 9. Dashboard — Section "Burn Rate"

| KPI / Graphique | Description |
|---|---|
| **Burn Rate — Argent brûlé en moyenne par jour** | Courbe mensuelle : total dépenses du mois / nombre de jours écoulés dans le mois. Affiché par mois pour suivre l'évolution. |

---

## 10. Vue Investissements (page dédiée)

Pour chaque compte d'investissement :

- **Solde de départ** (point zéro) avec sa date
- **Total versé** depuis le point zéro
- **Total retiré** depuis le point zéro
- **Montant net investi** (versements – retraits)
- **Valeur actuelle** (dernier snapshot)
- **Gain / Perte en €** (valeur actuelle – montant net investi)
- **Performance en %**
- **Historique des versements/retraits** (tableau)
- **Courbe de la valeur dans le temps**

### Fonctionnalité "Nouveau point zéro"

Bouton permettant de saisir la valeur actuelle comme nouvelle base de référence. L'historique précédent est archivé, les KPI repartent de ce nouveau point.

---

## 11. Vue Compte courant (page dédiée)

- **Solde actuel** (calculé depuis les transactions)
- **Tableau des transactions** filtrable par mois, catégorie, commerçant, type
- **Saisie rapide** : date, type (Entré/Sortie), commerçant, catégorie, montant
- Tous les graphiques de la section "Budget" et "Répartition" filtrés sur ce compte

---

## 12. Import des données existantes

### 12.1 Format CSV attendu (issu du tableur Numbers)

```csv
Date,Mois,Type,Commercant,Categorie,Montant,Solde Compte
01/01/2026 00:00,Janvier,Type,Solde Initial,,666.00,666.00
01/01/2026 00:00,Janvier,Entré,Denis,Remboursement (reçu),17.00,683.00
05/01/2026 00:00,Janvier,Sortie,CGR,Sortie,2.00,681.00
05/01/2026 00:00,Janvier,Sortie,KFC,Nourriture,14.85,666.15
```

**Colonnes :**

| Colonne | Type | Notes |
|---|---|---|
| Date | datetime `DD/MM/YYYY HH:MM` | |
| Mois | string | ex: "Janvier" |
| Type | enum | `Entré`, `Sortie`, `Type` (= Solde Initial) |
| Commercant | string | Nom du commerçant ou de la personne |
| Categorie | string | Doit être mappée aux catégories de l'app |
| Montant | decimal | Toujours positif |
| Solde Compte | decimal | Peut être recalculé, mais utile pour vérification |

### 12.2 Comportement de l'import

- Onglet "Importation" accessible depuis les paramètres (`/settings?tab=import`)
- L'utilisateur upload son fichier CSV
- **Aperçu avant import** : tableau des N premières lignes, détection automatique du format
- **Mapping des catégories** : si une catégorie du CSV n'existe pas dans l'app, proposer de la créer ou de la mapper vers une existante
- **Gestion des doublons** : si une ligne identique (même date, montant, commerçant) existe déjà, l'ignorer avec un avertissement
- **Rapport post-import** : nombre de lignes importées, ignorées, erreurs
- **Import incrémental** : possibilité de ré-importer un CSV plus récent sans écraser l'existant

### 12.3 Format CSV export

L'app doit aussi permettre d'exporter les transactions dans le même format CSV, pour compatibilité avec Numbers si besoin.

---

## 13. Saisie manuelle des données

Toutes les données peuvent être saisies manuellement en complément de l'import.

### Formulaires requis :
- Ajout / modification / suppression d'un compte
- Saisie d'une transaction (compte courant) : date, type, commerçant, catégorie, montant
- Saisie d'un versement ou retrait (comptes investissement)
- Saisie d'un snapshot de valeur (comptes investissement)
- Gestion des catégories (ajout, renommage, couleur, icône)
- Définition d'un nouveau point zéro sur un compte d'investissement

---

## 14. Stack technique recommandée

| Composant | Choix recommandé | Justification |
|---|---|---|
| Conteneurisation | **Docker + Docker Compose** | Déploiement simple, portable |
| Frontend | **React** (Vite) + **Recharts** | Réactif, Recharts couvre tous les graphiques requis |
| Backend / API | **FastAPI** (Python) | Simple, typage fort, parfait pour SQLite |
| Base de données | **SQLite** | Zéro configuration, fichier local, facile à sauvegarder |
| Style | **Tailwind CSS** | Rapide, propre |
| Parsing CSV | **pandas** (Python, côté backend) | Robuste pour l'import |

---

## 15. Architecture des pages / navigation

```
/ (Dashboard)
  ├── Filtre global : sélecteur de mois / année
  ├── Section Budget (KPI + tableau)
  ├── Section Répartition de l'argent (donuts + barres)
  ├── Section Top Dépenses
  ├── Section Dépenses dans le temps (courbes + histogrammes)
  ├── Section Investissement (donut + barres)
  └── Section Burn Rate

/comptes
  └── Liste de tous les comptes avec solde actuel

/comptes/:id
  └── Si investissement → Vue investissement détaillée
  └── Si courant → Vue transactions + graphiques filtrés

/import
  └── Upload CSV → aperçu → mapping → import
  └── Rapport d'import

/parametres
  └── Gestion des comptes (ajout/archivage/couleur)
  └── Gestion des catégories
  └── Export CSV
```

---

## 16. Fonctionnalités hors périmètre (v1)

- Import automatique de relevés bancaires (connexion API bancaire)
- Notifications / alertes
- Multi-utilisateurs
- Progression vers objectifs financiers (retraite, achat immo)
- Prix en temps réel (cours bourse, crypto)
- Application mobile native

---

## 17. Contraintes non-fonctionnelles

- **Usage 100% local** : aucune donnée ne quitte la machine hôte
- **Sauvegarde simple** : BDD SQLite dans un volume Docker dédié (`./data/`)
- **Responsive** : lisible sur desktop et tablette (mobile optionnel en v1)
- **Pas de dépendance à des services tiers** en dehors des librairies open source

---

## 19. Nouvelles fonctionnalités (v1.2)

### 19.1 Mode Confidentialité (Privacy Mode)
- **Objectif** : Flouter les montants financiers pour permettre l'usage de l'app en public.
- **UI** : Toggle (icône œil) dans la barre de navigation supérieure.
- **Comportement** : 
    - État persisté localement (localStorage).
    - Ajout d'une classe CSS globale ou utilisation de variables CSS pour appliquer un `filter: blur()` sur les éléments de classe `.amount-value`.
    - Affecte les KPI, les soldes dans les tableaux, et les montants dans les graphiques (si possible).

### 19.2 Vue Comparaison (Mois vs Mois)
- **Objectif** : Analyser les écarts de dépenses entre deux périodes.
- **UI** : Nouvelle page `/comparaison` ou onglet dans le Dashboard.
- **Fonctionnalités** :
    - Sélection de deux mois (ex: Avril 2026 vs Mars 2026).
    - Affichage en colonnes : [Catégorie] | [Mois A] | [Mois B] | [Différence €/%].
    - Indicateurs visuels (flèches rouges/vertes) pour les variations significatives.

---

## Annexe — Récapitulatif des graphiques à implémenter

| # | Graphique | Type | Données | Section |
|---|---|---|---|---|
| 1 | Sorties d'argent par catégorie | Donut | Dépenses du mois par catégorie | Répartition |
| 2 | Abonnements par commerçant | Donut | Transactions catégorie=Abonnement par commerçant | Répartition |
| 3 | Répartition sortie totale | Donut | Toutes sorties par catégorie | Répartition |
| 4 | Montant cumulé abonnements | Barres horizontales | Total par commerçant (Abonnement) | Répartition / Top |
| 5 | Total dépense par catégories | Barres verticales | Total par catégorie sur période | Top Dépenses |
| 6 | Top 5 Commerçants | Barres horizontales | Top 5 commerçants par total dépensé | Top Dépenses |
| 7 | Évolution compte courant | Courbe | Solde dans le temps (par transaction) | Temps |
| 8 | Total Entré/Sortie par mois | Histogramme groupé | Revenus vs Dépenses par mois | Temps |
| 9 | Évolution du salaire | Courbe | Salaire mensuel dans le temps | Temps |
| 10 | Répartition Investissement | Donut | Part de chaque compte d'investissement | Investissement |
| 11 | Versements mensuels par compte | Barres horizontales | Versement du mois par compte invest. | Investissement |
| 12 | Burn Rate moyen par jour | Courbe | Dépenses/jour par mois | Burn Rate |

---

*Document généré pour transmission à un agent IA de développement. Version 2.0.*
