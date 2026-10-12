<div align="center">

# 💰 Numera

**Application web self-hosted de finance personnelle**

Remplacez votre tableur par une vraie application : budget, comptes, investissements, objectifs d'épargne, comparaisons mensuelles, import/export CSV et sauvegardes chiffrées.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Stack technique](#-stack-technique)
- [Architecture](#-architecture)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Développement](#-développement)
- [Commandes utiles](#-commandes-utiles)
- [Serveur MCP](#-serveur-mcp)
- [Structure du projet](#-structure-du-projet)
- [Tests](#-tests)
- [Documentation](#-documentation)
- [Contribuer](#-contribuer)
- [Licence](#-licence)

---

## ✨ Fonctionnalités

| Module | Description |
|---|---|
| 📊 **Dashboard budget** | Vue d'ensemble des dépenses par catégorie, top marchands, timeseries et entrées/sorties |
| 🏦 **Gestion de comptes** | Multi-comptes avec solde initial, running balance et détail filtrable |
| 📈 **Investissements** | Suivi de flux, snapshots, performance, point zéro et simulation patrimoine |
| 🎯 **Objectifs d'épargne** | Définition et suivi de progression vers vos objectifs financiers |
| 🔄 **Comparaison mensuelle** | Analyse comparative mois par mois de vos habitudes |
| 💱 **Multi-devise** | Taux de change courants et historiques |
| 📥 **Import/Export CSV** | Import idempotent depuis Numbers/Excel avec preview et déduplication |
| 🔐 **Authentification** | Mono-admin JWT avec hash sécurisé |
| 💾 **Sauvegardes chiffrées** | Backup automatique SQLite avec chiffrement AES |
| 🔔 **Alertes & abonnements** | Notifications, suivi d'abonnements récurrents |
| 🏷️ **Tags & catégorisation** | Règles de catégorisation automatique et tags personnalisés |
| 💼 **Suivi de salaire & TT** | Gestion du salaire, suivi du télétravail (TT), tickets restaurant et génération de transactions |
| 🏷️ **Normalisation marchands** | Regroupement des libellés bancaires sous un marchand canonique et gestion des alias |
| ✅ **Vérification de solde** | Date de dernière vérification des comptes (`last_verified_at`) et rappels d'audit |
| 📅 **Calendrier financier** | Vue calendrier de vos transactions |
| 🔒 **Mode confidentialité** | Masquage des montants en un clic |

---

## 🛠 Stack technique

```
Frontend                Backend                 Infra
├── React 18            ├── FastAPI             ├── Docker Compose
├── TypeScript          ├── SQLAlchemy          ├── Nginx (prod)
├── Vite 5              ├── Alembic             ├── Backup sidecar
├── Tailwind CSS        ├── Pydantic v2         └── SQLite
├── Recharts            └── Python 3.12+
├── Radix UI
└── React Router 7
```

---

## 🏗 Architecture

```
┌─────────────┐     HTTP/JSON     ┌─────────────────┐     SQLAlchemy     ┌──────────┐
│   Frontend  │ ◄───────────────► │  Backend (API)   │ ◄───────────────► │  SQLite  │
│  React SPA  │    Bearer JWT     │    FastAPI        │                   │   .db    │
└─────────────┘                   └─────────────────┘                   └──────────┘
      :5173                             :8001                          backend/data/
```

1. L'utilisateur se connecte via `/login`
2. Le frontend stocke le JWT dans `localStorage`
3. `apiFetch()` ajoute le bearer token à chaque requête
4. FastAPI valide l'utilisateur via `get_current_user`
5. Les endpoints lisent/écrivent SQLite via SQLAlchemy
6. Les agrégats financiers sont calculés côté backend et renvoyés prêts à afficher

> Pour une documentation complète de l'architecture, voir [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 📦 Prérequis

- **Docker** & **Docker Compose** (recommandé)
- Ou bien, pour un développement sans Docker :
  - Python 3.12+
  - Node.js 18+ & npm
  - Make

---

## 🚀 Installation

### Installation rapide (une seule commande)

```bash
sudo /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Hugo-Galley/numera/main/install.sh)"
```

### Installation manuelle

```bash
# 1. Cloner le dépôt
git clone https://github.com/Hugo-Galley/numera.git
cd suivi-budget

# 2. Configurer l'environnement
make setup                # Prépare le .env et génère les clés de sécurité

# 3. Définir le mot de passe admin
python3 scripts/change_password.py votre_mot_de_passe
# Copiez le hash généré dans votre .env (ADMIN_PASSWORD_HASH)

# 4. Lancer en production
make prod
```

### Variables d'environnement

Copiez `.env.example` vers `.env` et configurez les variables suivantes :

| Variable | Description | Défaut |
|---|---|---|
| `SECRET_KEY` | Clé secrète JWT | *Générée par `make setup`* |
| `ADMIN_USERNAME` | Nom d'utilisateur admin | `admin` |
| `ADMIN_PASSWORD_HASH` | Hash bcrypt du mot de passe | — |
| `BACKUP_KEY` | Clé de chiffrement des sauvegardes | *Générée par `make setup`, obligatoire en production* |
| `CORS_ORIGINS` | Origines navigateur autorisées, séparées par des virgules | `http://localhost:8082` |

En production, le compose publie uniquement le frontend sur `127.0.0.1:8082`; l'API reste interne. Pour un accès distant, placez un reverse proxy TLS devant ce port et définissez son URL HTTPS dans `CORS_ORIGINS` si une application d'une autre origine doit appeler l'API.

---

## 💻 Développement

```bash
make dev    # Lance backend + frontend + backup sidecar via Docker Compose
```

L'application sera accessible sur :

| Service | URL |
|---|---|
| Frontend | [`http://localhost:5173`](http://localhost:5173) |
| Backend API | [`http://localhost:8001`](http://localhost:8001) |
| Health check | [`GET /health`](http://localhost:8001/health) |

---

## ⚡ Commandes utiles

```bash
# Développement
make dev                     # Lance l'environnement complet (backend + frontend + backup)
make down                    # Arrête tous les conteneurs

# Installation des dépendances
make backend-install         # Installe les dépendances Python dans .venv
make frontend-install        # npm install dans frontend/

# Données
make backend-seed-demo       # Charge un jeu de données de démonstration

# Sauvegardes
make backup-now              # Force une sauvegarde immédiate
make backup-restore FILE=backups/<fichier>.db.enc  # Restaure une sauvegarde

# Build
cd frontend && npm run build # Build de production du frontend
```

---

## 🔌 Serveur MCP

Numera embarque un serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) qui permet à des agents IA (comme Claude ou Cursor) d'interroger et d'analyser vos finances de manière fiable et sécurisée.

En production, le serveur MCP tourne dans le conteneur `mcp-server` et il est exposé par Nginx sur `https://<votre-domaine>/mcp`. Il n'y a ni SSH, ni copie locale, ni mot de passe dans une configuration.

### 🚀 Connecter Claude Code

1. Dans Numera : **Paramètres → Compte → Claude Code (MCP)**, cliquer sur **Générer un token**.
2. Copier la commande affichée (le token n'est montré qu'une fois) et la lancer dans un terminal :
   ```bash
   claude mcp add --transport http --scope user numera https://<votre-domaine>/mcp \
     --header "Authorization: Bearer nmr_…"
   ```
3. Vérifier avec `claude mcp list`.

Sécurité :
- seule l'empreinte SHA-256 du token est stockée, et chaque token est révocable individuellement depuis la même page ;
- l'interrupteur « Accès MCP » coupe tous les tokens immédiatement ;
- un token MCP n'a pas accès à `/admin` (profil, mot de passe, reset de la base, création de tokens) ;
- le serveur MCP ne détient aucun secret : il fait valider le token par l'API puis le transmet à chaque appel.

Détails techniques, mode local (stdio) et mode SQLite : [`mcp-server/README.md`](mcp-server/README.md).

---

### 🔍 Outils disponibles pour l'IA (Lecture seule)
* **Budgets & Dépenses** : `get_budget_summary`, `get_expenses_by_category`, `get_top_merchants`, `get_money_flow` (ciblage optionnel par `account_id`).
* **Suivi de Comptes** : `list_accounts` (filtrable par `type`), `get_account_balance_history`.
* **Investissements** : `get_investments_summary`, `get_investment_performance` (gains, baseline point zéro, PRU), `get_investment_performance_history`, `get_investments_allocation`, `get_investments_allocation_advanced`.
* **SQL sécurisé** : `execute_read_query` (permet des requêtes `SELECT` personnalisées avec limite automatique à 200 lignes).

---

## 📁 Structure du projet

```
numera/
├── backend/
│   ├── alembic/             # Migrations de base de données
│   ├── app/
│   │   ├── api/             # Endpoints REST (FastAPI routers)
│   │   ├── core/            # Config, finance, currency, errors, security
│   │   ├── db/              # Session SQLAlchemy
│   │   ├── models/          # Modèles ORM SQLAlchemy
│   │   └── schemas/         # Schémas Pydantic (validation)
│   ├── data/                # Base SQLite (dev)
│   ├── scripts/             # Backup, restore, seed, password
│   └── tests/               # Tests pytest
├── frontend/
│   └── src/
│       ├── components/      # Layout (Sidebar, Omnibox) et UI (Radix)
│       ├── lib/             # Client API, utilitaires, helpers
│       ├── pages/           # Routes / vues principales
│       └── providers/       # AuthProvider, UIProvider
├── infra/
│   └── docker-compose.yml   # Orchestration Docker
├── scripts/                 # Scripts utilitaires
├── backups/                 # Sauvegardes chiffrées
├── docs/                    # Documentation additionnelle
└── Makefile                 # Commandes de développement
```

---

## 🧪 Tests

```bash
# Tests backend
cd backend && python -m pytest tests/ -v

# Tests avec couverture
cd backend && python -m pytest tests/ -v --cov=app
```

---

## 📚 Documentation

| Document | Description |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Guide pour les agents Claude Code (commandes, règles métier, carte des docs) |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Architecture détaillée, flux de données et routes API |
| [`docs/`](docs/) | Backend (exploitation), Centre d'Actions, sauvegardes |
| [`ROADMAP.md`](ROADMAP.md) | État d'avancement, sprints terminés et backlog |
| [`PLAN.MD`](PLAN.MD) | Cahier des charges produit historique |
| [`TEST_PLAN.md`](TEST_PLAN.md) | Stratégie de tests et scénarios critiques |

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Voici comment participer :

1. **Fork** le projet
2. Créez votre branche (`git checkout -b feature/ma-feature`)
3. Commitez vos changements (`git commit -m 'feat: ajouter ma feature'`)
4. Pushez la branche (`git push origin feature/ma-feature`)
5. Ouvrez une **Pull Request**

> Merci de suivre les [Conventional Commits](https://www.conventionalcommits.org/) pour vos messages de commit.

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [`LICENSE`](LICENSE) pour plus de détails.

---

<div align="center">

Fait avec ❤️ par [@Hugo-Galley](https://github.com/Hugo-Galley)

</div>
