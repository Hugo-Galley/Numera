# TEST_PLAN.md

## Objectif

Eviter les regressions financieres et proteger les donnees locales. Les tests prioritaires couvrent import/export, soldes, KPI, investissements, multi-devise, auth et sauvegarde.

## Commandes

Backend:

```bash
cd backend && python -m pytest tests/ -v
```

Frontend:

```bash
cd frontend && npm run build
```

Il n'existe pas encore de script frontend `test`, `lint` ou `typecheck` dedie.

## Tests Existants

Fichiers présents dans `backend/tests/` :

- `test_anomaly_detection.py` : détection d'anomalies de dépenses sur les catégories (hausse soudaine par rapport aux 3 mois précédents).
- `test_asset_allocation.py` : allocation avancée d'actifs (classe, secteur, zone géographique).
- `test_auth.py` : validation de l'authentification mono-admin JWT et de l'accès aux routes protégées.
- `test_calendar.py` : calendrier financier mensuel et projections associées.
- `test_cashflow_projection.py` : projection de solde et de trésorerie sur 30/60/90 jours.
- `test_categorization_rules.py` : création, import et application automatique de règles de catégorisation.
- `test_filtering.py` : filtrage multicritères sur les transactions (catégories, montants, commerçants, tags, etc.).
- `test_import_and_analytics.py` : import/export CSV, déduplication, point zéro, snapshots de valeur et KPIs.
- `test_money_flow.py` : calculs de flux de trésorerie (entrées, sorties, épargne, investissements, reste).
- `test_p0_features.py` : mise à jour groupée (bulk update), alertes de budget (limites mensuelles/annuelles) et insights intelligents.
- `test_savings_goals.py` : objectifs d'épargne (CRUD, progression, date cible, montant recommandé).
- `test_simulation.py` : simulateur de patrimoine et calculs de rendement composés.
- `test_subscriptions.py` : détection et gestion des abonnements/charges fixes récurrentes.
- `test_tags.py` : création, assignation et filtrage par tags transversaux.
- `test_transfers.py` : détection et rapprochement des virements internes de compte à compte.
- `conftest.py` : configuration de test et isolation de la base SQLite en mémoire pour chaque test.

Couverture actuelle notable :

- Import CSV, délimiteurs, normalisation des en-têtes et déduplication.
- KPIs financiers, taux d'épargne, burn rate, fonds de sécurité.
- Point zéro pour les investissements et blocage d'opérations antérieures.
- Export CSV compatible Numbers multi-comptes et investissements.
- Projections de trésorerie et calendriers financiers.
- Règles locales d'auto-catégorisation et abonnements récurrents.
- Rapprochement automatique des transferts internes.
- Tags transversaux et multi-critères.
- Authentification JWT et protection de toutes les routes métier.
- Alertes de budget par catégories et détection d'anomalies.
- Simulateur de patrimoine et intérêts composés.

## Matrice Critique

### Import CSV

- Delimiters `,`, `;`, tabulation.
- Headers avec accents, espaces, variantes et BOM.
- Dates `dd/mm/YYYY`, `dd/mm/YYYY HH:MM`, formats ISO.
- Montants avec virgule, point, espaces, symbole euro.
- Mapping categories manuel par nom, id ou creation.
- Creation optionnelle des categories manquantes.
- Type exporte `Type` mappe vers `Solde Initial`.
- Doublons sur `(account_id, date, amount, merchant, type)`.
- Recalcul complet des `running_balance` apres commit.

### Transactions

- Creation `Entree`, `Sortie`, `Interets`, `Solde Initial`.
- Interdiction de plusieurs `Solde Initial` sur un compte.
- `Solde Initial` chronologiquement premier.
- Update date/type/montant recalcule `month_label` et `running_balance`.
- Delete recalcule le compte.
- Bulk update categorie, recurrence, type et marchand.
- Recherche marchands et filtre `search`.

### Analytics Budget

- Revenus mensuels hors `Solde Initial`.
- Revenus all-time avec traitement coherent du solde initial.
- Depenses reelles vs investissements/epargne internes.
- `Interets` et dividendes.
- Taux d'epargne borne.
- Burn rate mois courant et mois passe.
- Patrimoine net et conversion EUR.
- Filtres `month`, `year`, `account_id`.

### Investissements Et Snapshots

- Types `versement`, `retrait`, `dividende`.
- Rejet d'operation avant point zero si la regle est active.
- Un seul `is_zero_point=True` par compte.
- Performance EUR et pourcentage depuis point zero.
- Historique de performance.
- Allocation simple et avancee.
- Multi-devise sur operations et comptes.

### Objectifs D'epargne

- Creation, update, delete `/goals`.
- Calcul de progression par `keyword` dans note, marchand ou categorie.
- Conversion EUR des montants.
- Sens positif/negatif selon type transaction.

### Auth Et Securite

- Login valide retourne un bearer token.
- Login invalide echoue sans detail sensible.
- Routes metier sans token retournent `401`.
- `GET /health` reste public.
- Expiration token geree par le frontend.

### Export CSV

- Colonnes compatibles Numbers.
- Export multi-comptes.
- Export inclut investissements selon format attendu.
- Round-trip export -> import sans duplication inattendue.

### Backup Restore

- `make backup-now` genere un fichier `.db.enc` si `BACKUP_KEY` est renseignee, sinon un fichier `.db`.
- Retention supprime les anciens backups selon configuration.
- `make backup-restore FILE=...` restaure une base lisible.
- Mauvaise `BACKUP_KEY` echoue proprement.

## Scenarios E2E Prioritaires

1. Login -> dashboard charge -> logout ou expiration token redirige vers `/login`.
2. Import CSV complet -> categories inconnues mappees -> dashboard coherent.
3. Ajout depense manuelle -> solde compte et budget mis a jour.
4. Modification date ancienne -> tous les soldes suivants sont recalcules.
5. Ajout versement investissement + snapshot -> performance et allocation mises a jour.
6. Creation objectif epargne -> transaction avec keyword -> progression visible.
7. Export CSV -> reimport sur meme compte -> pas de doublons.
8. Backup -> reset base -> restore -> donnees presentes.

## Tests Manquants A Ajouter En Priorite

- **Backend** : Tous les tests critiques initialement planifiés (Auth JWT, calcul de progression des objectifs `/goals`, alertes de budget, insights, bulk update, transferts et multidevises) ont été créés et passent avec succès.
- **Sauvegarde/Restauration** : La procédure de sauvegarde chiffrée et de restauration a été validée via script (`make backup-restore` et `backend/scripts/restore.py`). Un test d'intégration automatique pourrait être ajouté dans la CI pour valider le round-trip complet.
- **Frontend** : Il n'existe actuellement aucun runner de test pour l'interface utilisateur (SPA React). L'ajout de Vitest (pour les tests unitaires des composants) et de Playwright/Cypress (pour les scénarios de bout en bout décrits ci-dessus) est la priorité technique pour le chantier de tests.

## Definition D'une Regression Bloquante

- Difference de solde ou KPI non expliquee.
- `Solde Initial` compte comme revenu/depense mensuelle.
- Import non idempotent.
- Perte de `original_amount` ou mauvaise conversion devise.
- Route metier accessible sans token.
- Sauvegarde impossible a restaurer.
