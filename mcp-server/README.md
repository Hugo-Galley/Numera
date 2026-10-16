# 🔌 Serveur MCP — Numera

Serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) permettant à Claude (Claude Code, Claude Desktop) d'interroger les données du suivi budgétaire, **en lecture seule**.

Le point d'entrée `server.py` est un **dispatcher** qui lance l'un des deux serveurs :

| Mode | Fichier | Fonctionnement | Outils |
|------|---------|----------------|--------|
| **API proxy** | `server_api.py` | Appelle l'API FastAPI avec un **token MCP** généré dans Numera. Reprend les KPI calculés par le backend. Recommandé, et seul mode du `docker-compose.prod.yml` (exposé sur `/mcp`). | 38 outils, 4 ressources, 6 prompts |
| **SQLite direct** | `server_sqlite.py` | Lit la base SQLite (connexion `mode=ro`). Installation locale, **stdio uniquement**. | 20 outils, 5 ressources, 3 prompts |

### Choix du mode

1. `MCP_MODE=api` ou `sqlite` : mode forcé.
2. Sinon, si `MCP_API_URL` est défini → API.
3. Sinon, si le fichier `MCP_DB_PATH` (défaut `../backend/data/suivi_budget.db`) existe → SQLite.
4. Sinon → API.

> Règle du projet : les KPI sont calculés par le backend. Le mode SQLite recalcule certains agrégats en SQL et peut diverger ; en cas de doute, utiliser le mode API.

---

## 🧰 Outils

**Lecture seule, dans les deux modes.** Aucun outil ne crée, modifie ou supprime de données, et l'API le garantit aussi : avec un token MCP, toute requête autre que `GET` reçoit un 403 (`Accès MCP en lecture seule`). Les modifications se font dans l'interface Numera.

### Mode API (`server_api.py`)

**Données**
`list_accounts`, `list_categories`, `list_transactions`, `get_transaction`, `search_transactions`, `list_merchants`, `list_recurring_transactions`, `list_savings_goals`, `list_tags`, `list_transfer_rules`, `list_reimbursement_claims`

**Analyses (via `/analytics/*`)**
`get_budget_summary`, `get_expenses_by_category`, `get_top_merchants`, `get_subscriptions`, `get_budget_alerts`, `get_insights`, `get_monthly_report`, `get_month_review`, `list_month_closures`, `get_kpi_history`, `get_cashflow_projection`, `get_money_flow`, `get_tax_overview`, `get_work_time`

**Investissements**
`get_portfolio`, `get_dividends`, `list_holdings`, `list_investment_transactions`, `list_etf_profiles`, `get_etf_profile`, `get_investments_summary`, `get_investment_performance` (gains, baseline point zéro, PRU), `get_investment_performance_history`, `get_investments_allocation`, `get_investments_allocation_advanced`, `get_patrimoine_allocation`, `get_diversity_scanner`

**Ressources** : `data://accounts`, `data://categories`, `data://tags`, `data://recurring-transactions`

**Prompts** : `analyze_month`, `audit_subscriptions`, `budget_review`, `categorize_uncategorized` (propose des catégories, à appliquer dans l'interface), `analyze_portfolio`, `analyze_etf_lookthrough`

### Mode SQLite (`server_sqlite.py`)

- **Données** : `list_accounts`, `list_categories`, `list_transactions`, `get_transaction`, `search_transactions`, `list_recurring_transactions`, `list_savings_goals`, `list_tags`
- **Analyses** : `get_budget_summary`, `get_expenses_by_category`, `get_income_vs_expenses`, `get_top_merchants`, `get_monthly_trends`, `get_account_balance_history`
- **Investissements** : `get_investments_summary`, `get_investment_performance`, `get_investment_performance_history`, `get_investments_allocation`, `get_investments_allocation_advanced`
- **SQL** : `execute_read_query` (SELECT uniquement, `LIMIT 200` forcé)
- **Ressources** : `data://accounts`, `data://categories`, `data://tags`, tables et schémas de la base
- **Prompts** : `analyze_month`, `audit_subscriptions`, `budget_review`

> Le mode SQLite recalcule certains agrégats en SQL et peut diverger du backend ; toute évolution du modèle de données impose de vérifier `server_sqlite.py`.

---

## 🔑 Connexion de Claude (Code / Desktop)

En production, `docker-compose.prod.yml` lance `mcp-server` (mode API, transport `streamable-http`, sans état) ; Nginx l'expose sur `https://<domaine>/mcp`. Aucun port publié, aucun secret dans le conteneur.

1. Numera → **Paramètres → Compte → Claude (MCP)** → **Générer un token** (`nmr_…`, affiché une seule fois).
2. Lancer la commande affichée :
   ```bash
   claude mcp add --transport http --scope user numera https://<domaine>/mcp \
     --header "Authorization: Bearer nmr_…"
   ```
3. `claude mcp list` doit afficher `numera` connecté.

### Claude Desktop

Claude Desktop ne sait pas envoyer d'en-tête `Authorization` à un serveur distant (ses « connecteurs personnalisés » attendent OAuth). On passe donc par le pont local [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) (**Node.js requis**). L'interface génère le bloc à fusionner dans `claude_desktop_config.json` (Réglages → Développeur → Modifier la configuration ; macOS : `~/Library/Application Support/Claude/`) :

```json
{
  "mcpServers": {
    "numera": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://<domaine>/mcp", "--header", "Authorization:${NUMERA_AUTH}"],
      "env": { "NUMERA_AUTH": "Bearer nmr_…" }
    }
  }
}
```

Le token passe par la variable d'environnement (`Authorization:${NUMERA_AUTH}` sans espace : contourne un bug d'échappement des arguments de Claude Desktop). Redémarrer Claude Desktop ensuite.

Chaîne d'authentification :

```
Claude Code ──Bearer nmr_…──▶ Nginx /mcp ──▶ mcp-server
   server_auth.py : GET /auth/whoami avec ce token (refus 401 sinon, validation gardée 30 s)
   chaque outil   : appel API avec ce même token (server_api.APIClient)
backend : get_current_user accepte le token (empreinte SHA-256 dans mcp_tokens),
          le refuse s'il est révoqué ou si l'accès MCP est coupé, et /admin le refuse toujours (403)
```

Révoquer un token ou couper « Accès MCP » prend effet immédiatement pour les données : les appels d'outils sont refusés par l'API, même pendant les 30 s où la validation du middleware est gardée en cache.

En dev (`make dev`), le service `mcp-server` écoute sur `8100` et Vite proxifie `/mcp` : la commande affichée par l'interface (`http://localhost:5173/mcp`) fonctionne telle quelle.

---

## 📦 Installation locale (stdio)

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
| `MCP_SERVER_NAME` | les deux | Nom affiché | `Numera` |
| `MCP_TRANSPORT` | les deux | `stdio`, `streamable-http`, `sse` (SQLite : `stdio` seulement) | `stdio` (l'image Docker met `streamable-http`) |
| `MCP_HOST` / `MCP_PORT` | HTTP/SSE | Écoute | `127.0.0.1` / `8100` (l'image Docker met `0.0.0.0`) |
| `MCP_API_URL` | API | URL de l'API : `http://backend:8001` dans Docker, `https://domaine/api` via Nginx | `http://localhost:8001` (l'image Docker met `http://backend:8001`) |
| `MCP_API_TOKEN` | API, stdio | Token MCP généré dans l'interface — **obligatoire en stdio**. En HTTP, ignoré : chaque client envoie le sien | — |
| `MCP_DB_PATH` | SQLite | Fichier SQLite | `../backend/data/suivi_budget.db` |

Plus aucun mot de passe : `MCP_API_USERNAME`, `MCP_API_PASSWORD` et `MCP_AUTH_TOKEN` n'existent plus.

### Client local en stdio (optionnel)

Mode API, par exemple pour Claude Code sans passer par `/mcp` :

```bash
claude mcp add --scope user numera-local \
  -e MCP_MODE=api -e MCP_API_URL=https://<domaine>/api -e MCP_API_TOKEN=nmr_… \
  -- python3 /chemin/absolu/numera/mcp-server/server.py
```

Mode SQLite (même machine que la base ; pas d'authentification, le fichier suffit) : `-e MCP_MODE=sqlite -e MCP_DB_PATH=/chemin/absolu/numera/backend/data/suivi_budget.db`.

---

## 🐳 Docker

Service `mcp-server` de `docker-compose.prod.yml` (toujours lancé, frontend Nginx en dépend) : mode API, `streamable-http` sur `8100` dans le réseau Docker seulement, `MCP_API_URL=http://backend:8001`. Bloc Nginx : `location = /mcp` dans `frontend/nginx.conf` (`proxy_buffering off` pour le flux SSE).

Le serveur est construit en `stateless_http` (pas d'affinité de session) et sans protection DNS rebinding de la lib `mcp` (elle n'accepte que `Host: localhost`, ce qui casse derrière Nginx ; inutile puisque l'accès repose sur un token bearer explicite).

Build manuel : `docker build -t numera-mcp ./mcp-server`.

---

## 🔒 Sécurité

- **Tokens MCP** : 256 bits aléatoires préfixés `nmr_`, seule l'empreinte SHA-256 est stockée (`mcp_tokens`), affichés une seule fois, révocables un par un, `last_used_at` mis à jour (au plus une fois par minute). Interrupteur global « Accès MCP » (`system_settings.mcp_enabled`).
- **Périmètre** : un token MCP est en **lecture seule** (`GET` uniquement, 403 sinon) et n'a **aucun accès à `/admin`** (profil, mot de passe, reset de la base, gestion des tokens).
- **Transport** : le token circule dans un en-tête ; en production, n'exposer Numera qu'en HTTPS.
- **Mode SQLite** : stdio uniquement (refuse de démarrer en HTTP) ; lecture via connexion `mode=ro` ; SQL brut limité aux `SELECT` (mots-clés `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `REPLACE`, `ATTACH`, `DETACH`, `PRAGMA` refusés), `LIMIT 200` forcé , aucune écriture.
- Logs sur stderr.

Tests : `cd mcp-server && python3 -m pytest test_server_auth.py -q` (middleware) et `backend/tests/test_mcp_tokens.py` (tokens côté API).

---

## 🧪 Exemples

- « Analyse mon budget de mai 2026 » → `get_budget_summary`, `get_expenses_by_category`, `get_top_merchants` (ou prompt `analyze_month`).
- « Audit de mes abonnements » → prompt `audit_subscriptions` (`get_subscriptions` en mode API).
- « Combien chez Amazon cette année ? » → `execute_read_query` (mode SQLite) ou `search_transactions`.
- « Analyse mon portefeuille » → prompts `analyze_portfolio` / `analyze_etf_lookthrough` (mode API).

---

## 📁 Structure

```
mcp-server/
├── server.py          # Dispatcher (choisit api ou sqlite)
├── server_api.py      # Mode proxy API, lecture seule (httpx, token MCP)
├── server_auth.py     # Validation des tokens par l'API (transports HTTP)
├── server_sqlite.py   # Mode SQLite direct
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```
