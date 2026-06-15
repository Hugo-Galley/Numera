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

### Frontend
- **Page** : `frontend/src/pages/Audit.tsx` (ex-Audit, maintenant Centre d'Actions).
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
PYTHONPATH=. pytest tests/test_import_and_analytics.py
```

*Note : Si vous avez des erreurs de module `jose`, vérifiez que votre `venv` est bien activé.*

**Points de vérification critiques :**
- L'endpoint doit retourner un `200 OK` même si la liste d'actions est vide.
- Les doublons doivent être ignorés s'ils ont le flag `is_duplicate_ignored`.
- Les suggestions de règles ne doivent pas apparaître pour des marchands ayant déjà une règle active.

### 2.2 Frontend (UI & Workflows)
Le test manuel est privilégié ici pour valider les interactions.

**Scénarios à tester :**
1.  **Action Audit** : Cliquer sur "Catégoriser" -> Modifier une transaction -> Vérifier que l'action disparaît après actualisation.
2.  **Action Budget** : Créer une dépense dépassant une limite -> L'action "Budget dépassé" doit apparaître.
3.  **Action Règle** : Créer 5 transactions avec le même marchand inconnu -> Une suggestion doit apparaître -> Cliquer sur "Créer la règle" -> Vérifier la création dans les paramètres.

---

## 3. Bonnes Pratiques & Maintenance

### Performance
L'endpoint `/actions` effectue plusieurs scans de la base de données. 
- **Optimisation** : Les scans de transferts internes et de doublons sont limités aux 90 derniers jours pour éviter des lenteurs sur de grosses bases de données.
- **Index** : Assurez-vous que les colonnes `merchant`, `date` et `category_id` sont indexées.

### Ajout d'une nouvelle action
Pour ajouter un nouveau type d'action :
1.  Ajoutez le type dans l'énumération du schéma `ActionItem`.
2.  Implémentez la détection dans `get_action_center` (backend).
3.  Si une modale spécifique est requise, ajoutez-la dans `Audit.tsx` et gérez le `action_type`.

### Pièges à éviter
- **Doubles appels** : Ne pas rafraîchir la liste complète (`loadActions`) trop souvent ; privilégier le rafraîchissement ciblé si possible.
- **IDs stables** : L'ID de l'action doit être déterministe (ex: `suggest-rule-{merchant}`) pour permettre au frontend de garder l'état local si nécessaire.
