# Centre d'Actions — Documentation & Tests

Ce document détaille le fonctionnement du **Centre d'Actions** (Priorité 2) et fournit les instructions pour tester et maintenir cette fonctionnalité sans encombre.

## 1. Architecture

Le Centre d'Actions centralise trois types de flux :
1.  **Audit (Data Integrity)** : Problèmes de structure (catégories manquantes, doublons).
2.  **Budget** : Alertes de dépassement basées sur les limites mensuelles.
3.  **Règles (Smart Suggestions)** : Suggestions de création de règles basées sur la récurrence des marchands.

### Backend
- **Endpoint unique** : `/analytics/actions`
- **Modèle de données** : Utilise les schémas Pydantic `ActionItem` et `ActionCenterResponse` dans `backend/app/schemas/insight.py`.
- **Logique** : Agrégation de fonctions de calcul existantes (`budget_alerts`, `data_audit`) et de nouvelles requêtes (suggestions de règles).

### Notifications push
- `core/notifications.py::run_notifications`, appelée par la tâche horaire : envoie vers ntfy et/ou Telegram les actions dont la sévérité atteint le minimum choisi (`notify.min_severity`, `medium` par défaut) et dont l'empreinte (`id|title|description`) n'est pas dans `notification_log`. Un `ActionItem.id` déterministe et une description qui reflète l'état (ex. « 104 % du budget ») sont donc nécessaires : changer la description renvoie l'alerte.
- Première activation : actions existantes marquées connues, un seul message de bienvenue. Plus de 5 nouvelles actions → un message groupé. Résumé le dimanche après 18 h (une fois par semaine ISO). Un canal en échec n'est jamais marqué envoyé.

### Frontend
- **Page** : `frontend/src/pages/Audit.tsx`, route `/audit` (Centre d'actions).
- **Composants clés** : 
    - `ActionCenter` : Gère le chargement et le routage des actions.
    - `TransactionEditor` : Interface de correction en ligne pour les audits.
    - `RuleCreatorModal` : Formulaire rapide pour transformer une suggestion en règle réelle.

---

## 2. Procédure de Test

### 2.1 Backend (Logique métier)
Pour tester sans problèmes d'environnement, assurez-vous de définir le `PYTHONPATH` et d'utiliser une base de données de test propre.

**Commande recommandée :**
```bash
cd backend
PYTHONPATH=. python3.11 -m pytest tests/test_data_audit.py tests/test_import_and_analytics.py
```

*Note : Si vous avez des erreurs de module (`jwt`, etc.), vérifiez que votre `venv` est bien activé.*

**Points de vérification critiques :**
- L'endpoint doit retourner un `200 OK` même si la liste d'actions est vide.
- Les doublons doivent être ignorés s'ils ont le flag `is_duplicate_ignored`.
- Les suggestions de règles ne doivent pas apparaître pour des marchands ayant déjà une règle active.
- Une règle ne s'applique qu'à l'import (et via « appliquer à tout ») : `suggest-rule-{merchant}` n'apparaît que si le marchand a au moins 5 transactions sur 6 mois **dont au moins une sans catégorie** (virements et lignes générées par une récurrence exclus) ; catégorie proposée = la plus fréquente.
- `suggest-normalization-{libellé}` n'apparaît que si un même marchand existe sous au moins deux écritures (clé `audit.py::merchant_key` : sans accents, casse, chiffres ni ponctuation) ; `metadata.variants` liste les libellés, tous ajoutés comme alias par la modale.

### 2.2 Frontend (UI & Workflows)
Le test manuel est privilégié ici pour valider les interactions.

**Scénarios à tester :**
1.  **Action Audit** : Cliquer sur "Catégoriser" -> Modifier une transaction -> Vérifier que l'action disparaît après actualisation.
2.  **Action Budget** : Créer une dépense dépassant une limite -> L'action "Budget dépassé" doit apparaître.
3.  **Action Règle** : Créer 5 transactions avec le même marchand, dont une sans catégorie -> Une suggestion doit apparaître -> Cliquer sur "Créer la règle" -> Vérifier la création dans les paramètres.

---

## 3. Bonnes Pratiques & Maintenance

### Performance
L'endpoint `/actions` effectue plusieurs scans de la base de données. 
- **Optimisation** : Les scans de transferts internes et de doublons sont limités aux 90 derniers jours pour éviter des lenteurs sur de grosses bases de données.
- **Index** : Assurez-vous que les colonnes `merchant`, `date` et `category_id` sont indexées.

### Ajout d'une nouvelle action
Pour ajouter un nouveau type d'action :
1.  Choisissez un `action_type` (chaîne libre dans `ActionItem`, schéma `insight.py` : `link`, `modal_categorize`, `modal_rule`, `modal_snapshot`, `modal_merchant`).
2.  Implémentez la détection dans `compute_action_center` (`backend/app/services/audit.py` ; la route `/analytics/actions` de `controllers/analytics/audit.py` ne fait que l'appeler). Les actions écartées sont filtrées via `dismissed_insights` (`POST /analytics/actions/dismiss`).
3.  Si une modale spécifique est requise, ajoutez-la dans `Audit.tsx` et gérez le `action_type`.

### Actions « dividendes » (`type: investments`)
- `dividends-unlinked-{account_id}` : dividendes sans titre (rattachement via `POST /investment-transactions/link-dividends`).
- `reconciliation-gap-{account_id}-{date}` : le dernier snapshot (relevé du courtier) s'écarte de plus de 2 % de la valeur calculée par Numera (opération, frais ou dividende manquant) ; calcul sans appel réseau d'historique.
- `dividend-missing-{account_id}-{ticker}` : position marquée distribuante (`pays_dividends`) sans dividende saisi depuis plus de 13 mois (saisie manuelle, aucun appel externe).

### Action « remboursements » (`type: audit`)
- `unallocated-reimbursements` : entrées de catégorie « Remboursement… » des 180 derniers jours non affectées à une créance (`reimbursement_offset = 0`), remontée seulement s'il existe au moins une créance ouverte. `action_type: link` vers `/reimbursements`. Aussi présente dans `/analytics/audit` (détail : `GET /analytics/audit/unallocated-reimbursements`). Requête partagée : `_unallocated_reimbursements_query` (`audit.py`).

### Action « salaire absent » (`type: audit`, `severity: high`)
- `missing-salary-{YYYY-MM}` (dernier mois manquant) : config de salaire active, mois des 3 derniers (et pas avant la création de la config) dont le jour de paie est passé, sans `SalaryMonth` et sans entrée de type salaire (marchand ou catégorie « Salaire… », ou `salary_category_id`) sur le compte de salaire. Jour de paie = celui du dernier `SalaryMonth`, sinon le 28. Rien n'est généré automatiquement (montant ou emploi peuvent avoir changé). `action_type: link` vers `/recurring?tab=salary`. Logique : `core/salary.py::find_missing_salary_months`.

### Action « hausse de prix » (`type: subscription`, `severity: medium`)
- `subscription-price-{account_id}-{clé}-{date}` : un abonnement ou prélèvement régulier a augmenté (détection `core/subscription_prices.py::detect_price_changes`, mêmes données que `price_changes` de `/analytics/subscriptions`). La date de la hausse fait partie de l'id : une hausse écartée ne revient pas, une nouvelle hausse si. `action_type: link` vers `/recurring?tab=subscriptions`. Les transactions `is_subscription_ignored` et les virements sont exclus.

### Action « sauvegarde » (`type: audit`, `severity: high`)
`backup-failing-<AAAAMMJJ de la dernière sauvegarde>` : aucune sauvegarde depuis 2 jours ou dernière tentative en échec (`core/backup.py::backup_status`). L'id change avec la sauvegarde suivante, masquer l'alerte ne la fait donc pas taire pour toujours. Rien tant que les sauvegardes ne sont pas en place.

### Pièges à éviter
- **Doubles appels** : Ne pas rafraîchir la liste complète (`loadActions`) trop souvent ; privilégier le rafraîchissement ciblé si possible.
- **IDs stables** : L'ID de l'action doit être déterministe (ex: `suggest-rule-{merchant}`) pour permettre au frontend de garder l'état local si nécessaire.
