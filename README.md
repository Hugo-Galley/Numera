# Numera

Pendant longtemps, j'ai suivi mon budget et mes placements dans un tableur Numbers. Ça marchait, jusqu'au jour où il y a eu trop d'onglets, trop de formules fragiles et plus aucune envie de l'ouvrir. Numera est l'application que j'ai écrite pour le remplacer.

C'est une appli web à héberger soi-même, pensée pour une seule personne. Les données restent dans un fichier SQLite sur votre machine. Les seuls appels vers l'extérieur servent à récupérer les taux de change (Frankfurter) et les cours de bourse (Yahoo Finance).

## Ce qu'on peut faire avec

**Le budget au quotidien.** On importe ses relevés bancaires en CSV : l'import repère les doublons, donc on peut réimporter le même fichier sans risque. Les transactions sont rangées par catégories, avec des règles automatiques et des tags. Les libellés bancaires illisibles (« CB CARREFOUR 1234 PARIS ») sont regroupés sous un seul marchand. Les virements entre ses propres comptes sont reconnus et ne faussent pas les dépenses.

**Le suivi du mois.** Un tableau de bord avec les dépenses par catégorie, les abonnements, les budgets qui débordent et une projection de trésorerie. Chaque mois a son bilan, avec un diagramme de flux qui montre où est parti l'argent. On peut aussi comparer deux mois, regarder un calendrier des transactions, ou ouvrir le centre d'actions, qui signale les incohérences (transactions sans catégorie, doublons) et propose des règles à créer.

**Les investissements.** On saisit les versements, achats, ventes et dividendes ; Numera en déduit les positions, le prix de revient et la performance, valorisés au cours du jour. Il y a aussi la composition des ETF détenus, une vue de la diversification par pays et par secteur, et un simulateur pour projeter son patrimoine.

**Le reste.** Les objectifs d'épargne, la fiscalité des enveloppes (PEA, PER, assurance-vie, livrets), le salaire avec les jours de télétravail et les tickets restaurant, les remboursements en attente (quand on avance de l'argent à quelqu'un) et les comptes en devises étrangères. Un bouton masque tous les montants, pratique quand quelqu'un regarde l'écran.

Enfin, Claude peut lire vos données (sans jamais les modifier) grâce au serveur MCP intégré. Voir [plus bas](#demander-à-claude).

## Installation

Il faut Docker avec Docker Compose, ainsi que `git`, `openssl` et `curl`. Ensuite :

```bash
git clone https://github.com/Hugo-Galley/numera.git
cd numera
./install.sh
```

Le script demande un identifiant et un mot de passe, génère les clés dans `.env`, construit les images et attend que l'appli réponde. Comptez quelques minutes la première fois. À la fin, Numera tourne sur http://localhost:8082.

Sans cloner le dépôt au préalable, cette commande fait la même chose :

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Hugo-Galley/numera/main/install.sh)"
```

Le script peut être relancé sans crainte : s'il trouve un `.env`, il propose de le garder et se contente de reconstruire et redémarrer.

> **Une chose à ne pas oublier :** les sauvegardes sont chiffrées avec la `BACKUP_KEY` de votre `.env`. Copiez-la ailleurs (gestionnaire de mots de passe, par exemple). Si vous perdez le serveur et cette clé, les sauvegardes ne servent plus à rien.

Pour voir à quoi ça ressemble avec des données fictives : `make backend-seed-demo`.

### À la main

Pour tout configurer soi-même :

```bash
make setup                                       # crée .env, génère SECRET_KEY et BACKUP_KEY
python3 scripts/change_password.py 'mot-de-passe' # nécessite bcrypt (pip install bcrypt)
```

Collez le hash obtenu dans `.env` **entre guillemets simples**, sinon Docker Compose prend les `$` pour des variables et la connexion échoue :

```
ADMIN_PASSWORD_HASH='$2b$12$...'
```

Puis `make prod`.

### Accès depuis l'extérieur

Par défaut, l'appli n'écoute que sur `127.0.0.1:8082`. Pour y accéder depuis votre téléphone ou ailleurs, mettez un reverse proxy en HTTPS devant (Caddy, Traefik, Nginx, un tunnel Cloudflare…). L'API et le serveur MCP passent par le même port, sous `/api` et `/mcp` : il n'y a rien d'autre à exposer.

### Mettre à jour

```bash
make upgrade   # git pull + reconstruction des conteneurs
```

Les migrations de la base s'appliquent toutes seules au démarrage.

## Sauvegardes

Un conteneur dédié fait une copie chiffrée de la base toutes les 24 heures dans `backups/` et garde les 7 derniers jours (réglable avec `BACKUP_INTERVAL_SECONDS` et `RETENTION_DAYS` dans `.env`). Pour en déclencher une tout de suite :

```bash
docker exec numera-backup-prod python scripts/backup.py
```

Pour restaurer, arrêtez l'appli (`make prod-down`) puis :

```bash
export BACKUP_KEY=...   # la clé de votre .env
PYTHONPATH=backend python3 backend/scripts/restore.py \
  backups/suivi_budget_AAAAMMJJ_HHMMSS.db.enc --dest backend/data/suivi_budget.db
```

Plus de détails dans [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

## Demander à Claude

Numera embarque un serveur [MCP](https://modelcontextprotocol.io) : on peut demander à Claude « combien j'ai dépensé en restaurants ce trimestre ? », « fais-moi le bilan de septembre » ou « mon portefeuille est-il trop concentré sur les États-Unis ? ». Claude répond à partir des mêmes chiffres que l'appli.

Pour le brancher, allez dans **Paramètres → Compte → Claude (MCP)**, générez un token et lancez la commande affichée. Elle ressemble à ceci :

```bash
claude mcp add --transport http --scope user numera https://votre-domaine/mcp \
  --header "Authorization: Bearer nmr_..."
```

Pour Claude Desktop, la même page fournit le bloc à coller dans `claude_desktop_config.json`.

L'accès est en lecture seule, et ce n'est pas qu'une promesse du serveur MCP : l'API elle-même refuse toute écriture faite avec un token MCP, ainsi que l'accès aux réglages du compte. Chaque token peut être révoqué depuis l'interface, et un interrupteur coupe tout d'un coup. La liste des outils et les autres modes de fonctionnement sont dans [mcp-server/README.md](mcp-server/README.md).

## Développer

```bash
make dev
```

Ça lance tout en mode développement avec rechargement à chaud : le frontend sur http://localhost:5173, l'API sur http://localhost:8001.

Sans Docker, il faut **Python 3.11 ou 3.12** (pas 3.14, `pydantic-core` ne s'y installe pas) et Node 20 ou plus :

```bash
cd backend
python3.12 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# dans un autre terminal
cd frontend && npm install && npm run dev
```

Avant de pousser quoi que ce soit : `make validate`, qui lance les tests backend puis le build du frontend. Pour un seul fichier de tests :

```bash
cd backend && PYTHONPATH=. python3.12 -m pytest tests/test_tags.py -v
```

### Comment c'est construit

Le frontend est en React 18 + TypeScript (Vite, Tailwind, shadcn/ui, Recharts), le backend en FastAPI avec SQLAlchemy 2, Alembic et Pydantic v2. En production, un Nginx sert le frontend et relaie `/api` vers FastAPI et `/mcp` vers le serveur MCP.

Une règle tient l'ensemble : tous les calculs (soldes, KPI, performances) sont faits par le backend, dans `backend/app/api/analytics/`. Le frontend se contente d'afficher. Ainsi l'appli et Claude voient toujours les mêmes chiffres.

```
backend/      API FastAPI, modèles, migrations Alembic, tests
frontend/     appli React
mcp-server/   serveur MCP
docs/         exploitation, centre d'actions, sauvegardes
```

Pour aller plus loin :

- [ARCHITECTURE.md](ARCHITECTURE.md) : modèle de données, routes de l'API, règles de calcul
- [docs/BACKEND.md](docs/BACKEND.md) : logs, déploiement, sécurité
- [docs/ACTION_CENTER.md](docs/ACTION_CENTER.md) : le centre d'actions
- [CLAUDE.md](CLAUDE.md) : les consignes pour les agents IA qui travaillent sur le code

## Contribuer

C'est d'abord un projet personnel, mais les issues et les pull requests sont bienvenues. Si vous touchez au schéma de la base, ajoutez une migration Alembic ; si vous changez une route ou une règle de calcul, mettez à jour `ARCHITECTURE.md`. Les messages de commit suivent les [Conventional Commits](https://www.conventionalcommits.org/).

## Licence

MIT, voir [LICENSE](LICENSE).
