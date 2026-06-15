# Numera — Backend Expert Skill

Ce guide contient les instructions spécifiques pour le développement du backend FastAPI de Numera.

## 1. Modèles de Données (SQLAlchemy)
- **Localisation** : `app/models/`
- **Contraintes** : 
    - Utiliser `Mapped` et `mapped_column` (SQLAlchemy 2.0).
    - Toujours ajouter des index sur les colonnes de recherche fréquente (`merchant`, `date`, `account_id`).

## 2. Schémas de Validation (Pydantic v2)
- **Localisation** : `app/schemas/`
- **Règles** :
    - Utiliser `from_attributes=True` dans la config pour la conversion depuis SQLAlchemy.
    - Préférer les types précis (ex: `condecimal`) pour les montants financiers.

## 3. Logique Financière (Core)
- **Conversions Devises** : Toujours passer par `app.core.currency.convert_amount` ou `get_exchange_rates`.
- **Calcul des Soldes** : Le `running_balance` d'une transaction est calculé par rapport à l'historique chronologique du compte. Utiliser les fonctions d'aide dans `app.core.finance`.
- **Récurrences** : Les transactions récurrentes sont stockées séparément et "projetées" dans le calendrier ou générées réellement via `app/core/recurring.py`.

## 4. Endpoints API
- **Routage** : Utiliser des `APIRouter` thématiques.
- **Dépendances** : Utiliser `get_db` pour la session SQL et `get_current_user` pour la protection des routes.
- **Réponses** : Toujours renvoyer des objets JSON structurés via les schémas Pydantic. Éviter les dictionnaires `dict` bruts.

## 5. Tests Backend
- **Pytest** : Les tests sont situés dans `tests/`.
- **Mocking** : Utiliser les fixtures de `conftest.py` pour une base de données de test SQLite en mémoire ou fichier temporaire.
- **Validation** : Vérifier non seulement le code de retour HTTP, mais aussi l'impact réel en base de données.
