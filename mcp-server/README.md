# 🔌 Serveur MCP — Suivi Budget

Serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) permettant à un agent IA d'interroger et manipuler la base de données du suivi budgétaire.

## 📋 Fonctionnalités

### 🔍 Outils de consultation (lecture seule)
| Outil | Description |
|-------|-------------|
| `list_accounts` | Liste tous les comptes avec soldes |
| `list_categories` | Liste les catégories (filtrable par type) |
| `list_transactions` | Liste les transactions avec filtres avancés |
| `get_transaction` | Détail complet d'une transaction |
| `search_transactions` | Recherche textuelle (marchand, note) |
| `list_recurring_transactions` | Abonnements et récurrences |
| `list_savings_goals` | Objectifs d'épargne |
| `list_tags` | Tags avec nombre d'utilisations |

### 📊 Outils d'analyse
| Outil | Description |
|-------|-------------|
| `get_budget_summary` | Résumé budget par catégorie pour un mois |
| `get_expenses_by_category` | Répartition des dépenses par catégorie |
| `get_income_vs_expenses` | Comparaison revenus / dépenses |
| `get_top_merchants` | Top marchands par montant |
| `get_monthly_trends` | Tendances mensuelles (N mois) |
| `get_account_balance_history` | Historique du solde d'un compte |

### ✏️ Outils d'écriture
| Outil | Description |
|-------|-------------|
| `add_transaction` | Ajouter une transaction |
| `update_transaction` | Modifier une transaction existante |
| `delete_transaction` | Supprimer une transaction |
| `add_category` | Ajouter une catégorie |
| `categorize_transaction` | Changer la catégorie d'une transaction |
| `bulk_categorize` | Catégoriser en masse par marchand |

### 🔒 SQL sécurisé
| Outil | Description |
|-------|-------------|
| `execute_read_query` | Requête SQL SELECT uniquement (LIMIT 200 forcé) |

### 💡 Prompts (templates pour l'IA)
| Prompt | Description |
|--------|-------------|
| `analyze_month` | Analyse détaillée d'un mois de budget |
| `audit_subscriptions` | Audit complet des abonnements |
| `budget_review` | Review complète des finances |

---

## 🚀 Installation

### Prérequis
- Python 3.12+
- Le fichier `suivi_budget.db` accessible

### Installation locale

```bash
cd mcp-server
pip install -r requirements.txt
```

### Vérification

```bash
# Tester le serveur avec l'Inspector MCP
npx -y @modelcontextprotocol/inspector python server.py
```

---

## ⚙️ Configuration

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `MCP_DB_PATH` | Chemin vers la base SQLite | `../backend/data/suivi_budget.db` |
| `MCP_SERVER_NAME` | Nom du serveur | `Suivi Budget MCP` |
| `MCP_TRANSPORT` | Transport : `stdio`, `streamable-http`, `sse` | `stdio` |
| `MCP_HOST` | Host d'écoute (HTTP/SSE) | `0.0.0.0` |
| `MCP_PORT` | Port d'écoute (HTTP/SSE) | `8100` |

---

## 🖥️ Utilisation avec Claude Desktop

Ajouter dans le fichier de configuration Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json` sur macOS) :

```json
{
  "mcpServers": {
    "suivi-budget": {
      "command": "python",
      "args": ["/chemin/absolu/vers/suivi-budget/mcp-server/server.py"],
      "env": {
        "MCP_DB_PATH": "/chemin/absolu/vers/suivi-budget/backend/data/suivi_budget.db"
      }
    }
  }
}
```

> 💡 **Conseil :** Utilisez des chemins absolus.

---

## 🖱️ Utilisation avec Cursor

Ajouter dans `.cursor/mcp.json` à la racine du projet :

```json
{
  "mcpServers": {
    "suivi-budget": {
      "command": "python",
      "args": ["mcp-server/server.py"],
      "env": {
        "MCP_DB_PATH": "backend/data/suivi_budget.db"
      }
    }
  }
}
```

---

## 🐳 Déploiement Docker (VPS)

### Build et run

```bash
cd mcp-server
docker build -t suivi-budget-mcp .
docker run -d \
  --name mcp-server \
  -v /chemin/vers/backend/data:/data:ro \
  -p 8100:8100 \
  -e MCP_TRANSPORT=streamable-http \
  suivi-budget-mcp
```

### Avec docker-compose (ajouter dans `docker-compose.prod.yml`)

```yaml
  mcp-server:
    build:
      context: ./mcp-server
    container_name: suivi-budget-mcp
    environment:
      - MCP_DB_PATH=/data/suivi_budget.db
      - MCP_TRANSPORT=streamable-http
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8100
    volumes:
      - ./backend/data:/data:ro
    ports:
      - "8100:8100"
    restart: always
```

> ⚠️ **Sécurité :** Le volume est monté en lecture seule (`:ro`). Les opérations d'écriture du MCP ouvrent leur propre connexion en écriture.

---

## 🔒 Sécurité

### Mesures implémentées

1. **Requêtes SQL brutes** : uniquement `SELECT`, avec `LIMIT 200` forcé
2. **Mots-clés interdits** : `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `REPLACE`, `ATTACH`, `DETACH`, `PRAGMA` sont bloqués dans les requêtes SQL brutes
3. **Outils structurés** : les écritures passent par des outils validés avec vérification des entrées
4. **Connexion read-only** : la DB est ouverte en lecture seule par défaut
5. **Mode WAL** : journaling WAL pour éviter les conflits de verrous avec le backend

### Recommandations pour la production

- **Reverse proxy** : Mettez le serveur MCP derrière un Nginx avec TLS
- **Accès réseau** : Ne pas exposer le port 8100 directement sur Internet
- **Backups** : La base est partagée avec le backend, les backups existants couvrent le MCP
- **Monitoring** : Les logs sont envoyés sur stderr

---

## 🧪 Exemples d'utilisation

### Demander une analyse mensuelle
> "Analyse mon budget du mois de mai 2026"

L'IA utilisera automatiquement `get_budget_summary`, `get_expenses_by_category`, `get_top_merchants`, etc.

### Ajouter une transaction
> "J'ai payé 45€ chez Carrefour aujourd'hui, compte courant"

L'IA utilisera `list_accounts` pour trouver le bon compte, puis `add_transaction`.

### Auditer les abonnements
> "Fais un audit de tous mes abonnements"

L'IA utilisera le prompt `audit_subscriptions` et les outils associés.

### Requête SQL personnalisée
> "Combien j'ai dépensé chez Amazon cette année ?"

L'IA utilisera `execute_read_query` avec une requête SELECT adaptée.

---

## 📁 Structure

```
mcp-server/
├── server.py          # Serveur MCP principal
├── requirements.txt   # Dépendances Python
├── Dockerfile         # Image Docker
├── .env.example       # Variables d'environnement
└── README.md          # Cette documentation
```
