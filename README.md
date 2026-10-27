<div align="center">

<h1>Numera</h1>

<p><strong>Budget, épargne et investissements, chez vous.</strong></p>

<p>
  <img alt="Self-hosted" src="https://img.shields.io/badge/self--hosted-SQLite-0f172a?style=flat-square">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React_18-20232a?style=flat-square&logo=react&logoColor=61DAFB">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white">
  <a href="LICENSE"><img alt="Licence MIT" src="https://img.shields.io/badge/licence-MIT-22c55e?style=flat-square"></a>
</p>

<p>
  <a href="#installation">Installation</a> ·
  <a href="#ce-quon-peut-faire-avec">Fonctionnalités</a> ·
  <a href="#demander-à-claude">Claude</a> ·
  <a href="#développer">Développer</a>
</p>

</div>

<br>

Pendant longtemps, j'ai suivi mon budget et mes placements dans un tableur Numbers. Ça marchait, jusqu'au jour où il y a eu trop d'onglets, trop de formules fragiles et plus aucune envie de l'ouvrir. Numera est l'application que j'ai écrite pour le remplacer.

C'est une appli web à héberger soi-même, pensée pour une seule personne. Vos données restent dans un fichier SQLite sur votre machine ; les seuls appels vers l'extérieur servent à récupérer les taux de change et les cours de bourse.

<br>

## Ce qu'on peut faire avec

<table>
<tr>
<td width="50%" valign="top">

### Le budget au quotidien

Import des relevés bancaires en CSV, sans doublons même si on réimporte le même fichier. Catégories, règles automatiques et tags. Les libellés illisibles (« CB CARREFOUR 1234 PARIS ») sont regroupés sous un seul marchand, et les virements entre vos propres comptes ne faussent pas les dépenses.

</td>
<td width="50%" valign="top">

### Le suivi du mois

Dépenses par catégorie, abonnements, budgets qui débordent, projection de trésorerie. Un bilan mensuel avec le flux de l'argent, la comparaison entre deux mois, un calendrier, et un centre d'actions qui signale les incohérences à corriger.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Les investissements

Versements, achats, ventes et dividendes : Numera en déduit les positions, le prix de revient et la performance au cours du jour. Composition des ETF, diversification par pays et par secteur, simulateur de patrimoine.

</td>
<td width="50%" valign="top">

### Et le reste

Objectifs d'épargne, fiscalité des enveloppes (PEA, PER, assurance-vie, livrets), salaire avec télétravail et tickets restaurant, remboursements en attente, comptes en devises. Un bouton masque tous les montants quand quelqu'un regarde l'écran.

</td>
</tr>
</table>

<br>

## Installation

Il vous faut Docker (avec Compose), `git`, `openssl` et `curl`.

```bash
git clone https://github.com/Hugo-Galley/numera.git
cd numera
./install.sh
```

Le script demande un identifiant et un mot de passe, génère les clés, construit les images et attend que tout réponde. Quelques minutes plus tard, Numera tourne sur **http://localhost:8082**.

Le script peut être relancé sans crainte : s'il trouve une configuration existante, il la garde et se contente de redémarrer.

> [!IMPORTANT]
> Les sauvegardes sont chiffrées avec la `BACKUP_KEY` de votre fichier `.env`. Copiez-la quelque part (dans un gestionnaire de mots de passe, par exemple) : sans elle, une sauvegarde ne sert à rien.

> [!TIP]
> Pour essayer avec des données fictives : `make backend-seed-demo`.

<details>
<summary><strong>Installer sans cloner le dépôt</strong></summary>

<br>

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Hugo-Galley/numera/main/install.sh)"
```

Le dépôt est cloné dans `./numera`, puis l'installation se déroule comme ci-dessus.

</details>

<details>
<summary><strong>Tout configurer à la main</strong></summary>

<br>

```bash
make setup                                        # crée .env, génère SECRET_KEY et BACKUP_KEY
python3 scripts/change_password.py 'mot-de-passe' # nécessite bcrypt (pip install bcrypt)
```

Collez le hash obtenu dans `.env` **entre guillemets simples**, sinon Docker Compose prend les `$` pour des variables et la connexion échoue :

```env
ADMIN_PASSWORD_HASH='$2b$12$...'
```

Puis lancez `make prod`.

</details>

<details>
<summary><strong>Y accéder depuis l'extérieur</strong></summary>

<br>

Par défaut, l'appli n'écoute que sur `127.0.0.1:8082`. Pour l'ouvrir depuis votre téléphone, mettez un reverse proxy HTTPS devant : Caddy, Traefik, Nginx ou un tunnel Cloudflare. L'API (`/api`) et le serveur MCP (`/mcp`) passent par ce même port, il n'y a rien d'autre à exposer.

</details>

### Mettre à jour

```bash
make upgrade
```

Ça récupère la dernière version et reconstruit les conteneurs. Les migrations de la base s'appliquent toutes seules au démarrage.

<br>

## Sauvegardes

Toutes les 24 heures, une copie chiffrée de la base est déposée dans `backups/` ; les 7 derniers jours sont conservés (`BACKUP_INTERVAL_SECONDS` et `RETENTION_DAYS` dans `.env`).

```bash
# Sauvegarder tout de suite
docker exec numera-backup-prod python scripts/backup.py

# Restaurer (après make prod-down)
export BACKUP_KEY=...
PYTHONPATH=backend python3 backend/scripts/restore.py \
  backups/suivi_budget_AAAAMMJJ_HHMMSS.db.enc --dest backend/data/suivi_budget.db
```

Plus de détails dans [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

<br>

## Demander à Claude

Numera embarque un serveur [MCP](https://modelcontextprotocol.io). Une fois branché, on peut demander à Claude :

> *« Combien j'ai dépensé en restaurants ce trimestre ? »*<br>
> *« Fais-moi le bilan de septembre. »*<br>
> *« Mon portefeuille est-il trop concentré sur les États-Unis ? »*

Claude répond à partir des mêmes chiffres que l'appli. Pour le connecter, allez dans **Paramètres → Sécurité → Claude (MCP)**, générez un token et lancez la commande affichée :

```bash
claude mcp add --transport http --scope user numera https://votre-domaine/mcp \
  --header "Authorization: Bearer nmr_..."
```

Pour Claude Desktop, la même page fournit le bloc à coller dans `claude_desktop_config.json`.

L'accès est **en lecture seule**, et c'est l'API elle-même qui l'impose : elle refuse toute écriture faite avec un token MCP, ainsi que l'accès aux réglages du compte. Chaque token se révoque depuis l'interface, et un interrupteur coupe tout d'un coup. La liste des outils est dans [mcp-server/README.md](mcp-server/README.md).

<br>

## Développer

```bash
make dev
```

Frontend sur http://localhost:5173, API sur http://localhost:8001, avec rechargement à chaud des deux côtés. Avant de pousser : `make validate` (tests backend et build du frontend).

<details>
<summary><strong>Sans Docker</strong></summary>

<br>

Il faut **Python 3.11 ou 3.12** (`pydantic-core` ne s'installe pas sous 3.14) et Node 20 ou plus.

```bash
cd backend
python3.12 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# dans un autre terminal
cd frontend && npm install && npm run dev
```

Pour un seul fichier de tests : `cd backend && PYTHONPATH=. python3.12 -m pytest tests/test_tags.py -v`.

</details>

### Comment c'est construit

```
 Navigateur ──▶ Nginx ──┬── /       appli React (Vite, Tailwind, shadcn/ui, Recharts)
                        ├── /api ──▶ FastAPI ──▶ SQLite
 Claude ──────▶         └── /mcp ──▶ serveur MCP ──▶ FastAPI (lecture seule)
```

Le backend utilise FastAPI, SQLAlchemy 2, Alembic et Pydantic v2. Une règle tient l'ensemble : **tous les calculs sont faits par le backend** (`backend/app/api/analytics/`), le frontend se contente d'afficher. C'est ce qui garantit que l'appli et Claude voient les mêmes chiffres.

| Pour aller plus loin | |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | modèle de données, routes de l'API, règles de calcul |
| [docs/BACKEND.md](docs/BACKEND.md) | logs, déploiement, sécurité |
| [docs/ACTION_CENTER.md](docs/ACTION_CENTER.md) | le centre d'actions |
| [CLAUDE.md](CLAUDE.md) | consignes pour les agents IA qui travaillent sur le code |

<br>

## Contribuer

C'est d'abord un projet personnel, mais les issues et les pull requests sont les bienvenues. Si vous touchez au schéma, ajoutez une migration Alembic ; si vous changez une route ou un calcul, mettez à jour `ARCHITECTURE.md`. Les commits suivent les [Conventional Commits](https://www.conventionalcommits.org/).

<br>

<div align="center">
<sub>MIT · fait par <a href="https://github.com/Hugo-Galley">@Hugo-Galley</a></sub>
</div>
