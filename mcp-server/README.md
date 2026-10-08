# 🔌 Serveur MCP — Numera

Serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) permettant à un agent IA (Claude, Cursor…) d'interroger et de manipuler les données du suivi budgétaire.

Le point d'entrée `server.py` est un **dispatcher** qui lance l'un des deux serveurs :

| Mode | Fichier | Fonctionnement | Outils |
|------|---------|----------------|--------|
| **API proxy** | `server_api.py` | Appelle l'API FastAPI (login JWT via `/auth/token`). Reprend les KPI calculés par le backend. Recommandé, et seul mode du `docker-compose.prod.yml`. | 48 outils, 4 ressources, 6 prompts |
| **SQLite direct** | `server_sqlite.py` | Lit la base SQLite (connexion read-only), écritures par une connexion dédiée. Pour une installation locale. | 26 outils, 5 ressources, 3 prompts |

### Choix du mode

1. `MCP_MODE=api` ou `sqlite` : mode forcé.
2. Sinon, si `MCP_API_URL` est défini → API.
3. Sinon, si le fichier `MCP_DB_PATH` (défaut `../backend/data/suivi_budget.db`) existe → SQLite.
4. Sinon → API.

> Règle du projet : les KPI sont calculés par le backend. Le mode SQLite recalcule certains agrégats en SQL et peut diverger ; en cas de doute, utiliser le mode API.

---

## 🧰 Outils

### Mode API (`server_api.py`)

**Lecture — données**
`list_accounts`, `list_categories`, `list_transactions`, `get_transaction`, `search_transactions`, `list_merchants`, `list_recurring_transactions`, `list_savings_goals`, `list_tags`, `list_holdings`, `list_investment_transactions`, `list_etf_profiles`, `get_etf_profile`

**Lecture — analyses (via `/analytics/*`)**
`get_budget_summary`, `get_expenses_by_category`, `get_top_merchants`, `get_subscriptions`, `get_budget_alerts`, `get_insights`, `get_monthly_report`, `get_kpi_history`, `get_cashflow_projection`, `get_money_flow`

**Lecture — investissements**
`get_investments_summary`, `get_investment_performance` (gains, baseline point zéro, PRU), `get_investment_performance_history`, `get_investments_allocation`, `get_investments_allocation_advanced`, `get_patrimoine_allocation`, `get_diversity_scanner`

**Écriture**
`add_transaction`, `update_transaction`, `delete_transaction`, `bulk_update_transactions`, `categorize_transaction`, `bulk_categorize_by_merchant`, `add_category`, `add_recurring_transaction`, `add_holding`, `delete_holding`, `add_investment_transaction`, `delete_investment_transaction`

**Ressources** : `data://accounts`, `data://categories`, `data://tags`, `data://recurring-transactions`

**Prompts** : `analyze_month`, `audit_subscriptions`, `budget_review`, `categorize_uncategorized`, `analyze_portfolio`, `analyze_etf_lookthrough`

### Mode SQLite (`server_sqlite.py`)

- **Lecture** : `list_accounts`, `list_categories`, `list_transactions`, `get_transaction`, `search_transactions`, `list_recurring_transactions`, `list_savings_goals`, `list_tags`
- **Analyses** : `get_budget_summary`, `get_expenses_by_category`, `get_income_vs_expenses`, `get_top_merchants`, `get_monthly_trends`, `get_account_balance_history`
- **Investissements** : `get_investments_summary`, `get_investment_performance`, `get_investment_performance_history`, `get_investments_allocation`, `get_investments_allocation_advanced`
- **Écriture** : `add_transaction`, `update_transaction`, `delete_transaction`, `add_category`, `categorize_transaction`, `bulk_categorize`
- **SQL** : `execute_read_query` (SELECT uniquement, `LIMIT 200` forcé)
- **Ressources** : `data://accounts`, `data://categories`, `data://tags`, tables et schémas de la base
- **Prompts** : `analyze_month`, `audit_subscriptions`, `budget_review`

Les outils d'écriture du mode API passent par l'API : les `running_balance` sont recalculés par le backend.

> ⚠️ **Limite du mode SQLite** : `add_transaction` calcule le solde à partir de la dernière transaction du compte, mais `update_transaction` et `delete_transaction` ne recalculent pas les `running_balance`, et un ajout daté dans le passé laisse les soldes suivants faux. Pour toute écriture, préférer le mode API ; sinon, corriger ensuite les soldes via l'API (modifier une transaction depuis l'interface relance le recalcul du compte). Toute évolution du modèle de données impose de vérifier `server_sqlite.py`.

---

## 📦 Installation

Prérequis : Python 3.12+.

```bash
cd mcp-server
pip install -r requirements.txt     # mcp[cli]>=1.9.0 (httpx arrive avec mcp)

# Tester avec l'Inspector MCP
npx -y @modelcontextprotocol/inspector python server.py
```

## ⚙️ Variables d'environnement

| Variable | Mode | Description | Défaut |
|----------|------|-------------|--------|
| `MCP_MODE` | les deux | Force `api` ou `sqlite` | auto |
| `MCP_SERVER_NAME` | les deux | Nom affiché | `Suivi Budget MCP` |
| `MCP_TRANSPORT` | les deux | `stdio`, `streamable-http`, `sse` | `stdio` (l'image Docker met `streamable-http`) |
| `MCP_HOST` / `MCP_PORT` | HTTP/SSE | Écoute | `127.0.0.1` / `8100` (l'image Docker met `0.0.0.0`) |
| `MCP_AUTH_TOKEN` | HTTP/SSE | Token bearer exigé de tous les clients (`Authorization: Bearer …`), 16 caractères minimum — **obligatoire**, le serveur refuse de démarrer en HTTP sans. Génération : `openssl rand -hex 32` | — |
| `MCP_DB_PATH` | SQLite | Fichier SQLite | `../backend/data/suivi_budget.db` |
| `MCP_API_URL` | API | URL de l'API. Derrière le Nginx de prod, **terminer par `/api`** (ex. `http://hote:8082/api`) ; en direct sur le backend, `http://backend:8001` | `http://192.168.1.100:8001` (valeur d'exemple à remplacer) |
| `MCP_API_USERNAME` | API | Compte admin | `admin` |
| `MCP_API_PASSWORD` | API | Mot de passe admin — **obligatoire**, le serveur refuse de démarrer sans | — |

---

## 🖥️ Claude Desktop / Cursor

**Mode SQLite (installation locale)**

```json
{
  "mcpServers": {
    "numera": {
      "command": "python",
      "args": ["/chemin/absolu/numera/mcp-server/server.py"],
      "env": {
        "MCP_MODE": "sqlite",
        "MCP_DB_PATH": "/chemin/absolu/numera/backend/data/suivi_budget.db"
      }
    }
  }
}
```

**Mode API (instance distante)**

```json
{
  "mcpServers": {
    "numera": {
      "command": "python",
      "args": ["/chemin/absolu/numera/mcp-server/server.py"],
      "env": {
        "MCP_MODE": "api",
        "MCP_API_URL": "https://votre-domaine/api",
        "MCP_API_USERNAME": "admin",
        "MCP_API_PASSWORD": "••••••••"
      }
    }
  }
}
```

Claude Desktop : `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS). Cursor : `.cursor/mcp.json` à la racine du projet. Utiliser des chemins absolus.

---

## 🐳 Docker

Le service est déclaré dans `docker-compose.prod.yml` sous le **profil `mcp`** (non lancé par défaut), en mode API, transport `stdio`, **sans port publié** :

```bash
MCP_API_PASSWORD=... docker compose --env-file .env -f docker-compose.prod.yml --profile mcp up -d mcp-server
```

Il cible `http://backend:8001` dans le réseau Docker. Les transports HTTP (`sse`, `streamable-http`) exigent `MCP_AUTH_TOKEN` (token bearer, `server_auth.py`) et refusent de démarrer sans. Le token ne chiffre rien : pour une exposition hors réseau local, ajouter TLS (reverse proxy). Le transport `stdio` n'est pas concerné.

Build manuel de l'image : `docker build -t numera-mcp ./mcp-server` (l'image définit `MCP_DB_PATH=/data/suivi_budget.db` et `MCP_TRANSPORT=streamable-http` ; en mode API, surcharger `MCP_MODE`, `MCP_API_URL`, `MCP_API_PASSWORD` et `MCP_TRANSPORT`).

---

## 🔒 Sécurité

- **Mode API** : toutes les règles du backend s'appliquent (JWT, limitation des tentatives de login). Le mot de passe admin est fourni par variable d'environnement, jamais dans le dépôt.
- **Mode SQLite** : lecture via connexion `mode=ro` ; SQL brut limité aux `SELECT` (mots-clés `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `REPLACE`, `ATTACH`, `DETACH`, `PRAGMA` refusés), `LIMIT 200` forcé ; écritures par outils validés uniquement ; journal WAL pour cohabiter avec le backend.
- Les écritures de l'agent (ajout, suppression, catégorisation en masse) modifient vraiment les données : faire une sauvegarde (`make backup-now`) avant une session de nettoyage en masse.
- Logs sur stderr.

---

## 🧪 Exemples

- « Analyse mon budget de mai 2026 » → `get_budget_summary`, `get_expenses_by_category`, `get_top_merchants` (ou prompt `analyze_month`).
- « J'ai payé 45 € chez Carrefour aujourd'hui » → `list_accounts` puis `add_transaction`.
- « Audit de mes abonnements » → prompt `audit_subscriptions` (`get_subscriptions` en mode API).
- « Combien chez Amazon cette année ? » → `execute_read_query` (mode SQLite) ou `search_transactions`.
- « Analyse mon portefeuille » → prompts `analyze_portfolio` / `analyze_etf_lookthrough` (mode API).

---

## 📁 Structure

```
mcp-server/
├── server.py          # Dispatcher (choisit api ou sqlite)
├── server_api.py      # Mode proxy API (httpx + JWT)
├── server_sqlite.py   # Mode SQLite direct
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```
