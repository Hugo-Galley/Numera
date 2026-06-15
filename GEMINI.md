# Numera — Guide de Développement (Agent Skill)

Ce guide définit les standards d'ingénierie, les modèles architecturaux et les flux de travail pour le projet Numera. Tout agent (IA ou humain) intervenant sur ce dépôt doit s'y conformer rigoureusement.

## 1. Principes Fondamentaux

- **Local-First & Privacy** : Aucune donnée ne doit quitter la machine (sauf taux de change via Frankfurter). Pas de télémétrie.
- **Backend-Driven Calculation** : Tous les calculs financiers complexes (soldes, KPI, analytics) s'effectuent côté backend (Python). Le frontend (React) est purement présentatif.
- **Single Admin** : L'application est mono-utilisateur. L'authentification utilise un JWT simple (`admin`).
- **Data Integrity First** : Toute modification sur les transactions doit recalculer le `running_balance`.

## 2. Skill Usage & Activation

Pour chaque tâche, l'agent **DOIT** activer le skill spécialisé approprié via `activate_skill` dès le premier tour :

| Skill | Quand l'activer ? |
|---|---|
| `numera-expert` | Pour toute question générale sur le projet, l'architecture ou les modèles de données. |
| `numera-backend` | Dès qu'une modification est requise dans `backend/app/` (API, Modèles, Core). |
| `numera-design-ux` | Dès qu'une modification touche au `frontend/src/` (Composants, Pages, Styles). |
| `numera-testing` | Avant toute phase de validation, ou pour corriger des tests en échec. |

*Note : Plusieurs skills peuvent être activés si la tâche est transverse.*

## 3. Architecture Technique

### Backend (FastAPI + SQLAlchemy + SQLite)
- **Localisation** : `/backend`
- **Modèles** : `app/models/` (SQLAlchemy)
- **Schémas** : `app/schemas/` (Pydantic v2)
- **API** : `app/api/` (Endpoints REST)
- **Core** : `app/core/` (Logique métier, devises, sécurité)
- **Tests** : `tests/` (Pytest)

### Frontend (React + Vite + Tailwind + shadcn/ui)
- **Localisation** : `/frontend`
- **Pages** : `src/pages/`
- **Composants** : `src/components/`
- **API** : `src/lib/api.ts` (Utiliser `apiFetch` pour les appels JSON)
- **Style** : Tailwind CSS + shadcn/ui (Vanilla CSS préféré pour les personnalisations)

## 3. Standards de Code & Conventions

### Backend
- **Type Hinting** : Toujours typer les arguments et les retours de fonctions.
- **Gestion des Devises** : Utiliser `app.core.currency.get_exchange_rates` pour les conversions. Toujours stocker la valeur convertie dans la devise du compte (`amount`) et garder la saisie originale (`original_amount`, `currency`).
- **Migrations** : Utiliser Alembic pour tout changement de schéma. Les migrations sont lancées automatiquement au démarrage via `app/core/migrations.py`.
- **Logs** : Utiliser le logger de `app.core.logging`.

### Frontend
- **Typescript** : Typage strict obligatoire. Éviter les `any`.
- **Composants UI** : Utiliser les composants `shadcn` situés dans `@/components/ui`.
- **État Global** : Utiliser `UIProvider` pour l'interface et `AuthProvider` pour la session.
- **Icônes** : Utiliser `lucide-react`.

## 4. Workflows Spécifiques

### Recherche & Planification
- Toujours consulter `ARCHITECTURE.md` et `ROADMAP.md` avant de commencer une tâche.
- Pour les fonctionnalités complexes, créer un plan dans `PLAN.MD` ou via un fichier `.md` temporaire.

### Modification de la Base de Données
1. Modifier le modèle dans `backend/app/models/`.
2. Générer la migration : `cd backend && alembic revision --autogenerate -m "description"`.
3. Vérifier la migration générée dans `backend/alembic/versions/`.

### Ajout d'un KPI / Graphe
1. Implémenter le calcul dans `backend/app/api/analytics.py`.
2. Créer/Mettre à jour le schéma Pydantic dans `backend/app/schemas/insight.py`.
3. Consommer l'endpoint dans le frontend et afficher via `recharts`.

## 5. Tests & Validation

### Backend
Exécuter les tests avec :
```bash
cd backend && PYTHONPATH=. pytest
```
Toujours ajouter un test pour chaque nouveau bug corrigé ou nouvelle fonctionnalité.

### Frontend
Vérifier le build :
```bash
cd frontend && npm run build
```

## 6. Sécurité & Données
- **NE JAMAIS** commiter le fichier `backend/data/suivi_budget.db`.
- **NE JAMAIS** logger les tokens JWT en clair.
- Respecter le `Mode Confidentialité` (Privacy Mode) qui floute les montants dans l'UI.
