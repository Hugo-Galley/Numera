# 🔌 Serveur MCP — Numera

Serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) permettant à un agent IA (Claude, Cursor…) d'interroger et de manipuler les données du suivi budgétaire.

Le point d'entrée `server.py` est un **dispatcher** qui lance l'un des deux serveurs :

| Mode | Fichier | Fonctionnement | Outils |
|------|---------|----------------|--------|
| **API proxy** | `server_api.py` | Appelle l'API FastAPI avec un **token MCP** généré dans Numera. Reprend les KPI calculés par le backend. Recommandé, et seul mode du `docker-compose.prod.yml` (exposé sur `/mcp`). | 53 outils, 4 ressources, 6 prompts |
| **SQLite direct** | `server_sqlite.py` | Lit la base SQLite (connexion read-only), écritures par une connexion dédiée. Installation locale, **stdio uniquement**. | 26 outils, 5 ressources, 3 prompts |

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

> ⚠️ **Limite du mode SQLite** : `add_transaction` calcule le solde à partir de la dernière transaction du compte, mais `update_transaction` et `delete_transaction` ne recalculent pas les `running_balance`, et un ajout daté dans le passé laisse les soldes suivants faux. Pour toute écriture, préférer le mode API ; sinon, corriger ensuite les soldes via l'API (modifier une transaction depuis l'interface relance le recalcul du compte). Toute évolution du modèle de données impose de vérifier `server_sqlite.py`. Il ignore aussi les remboursements : modifier le montant ou le type, ou supprimer une transaction qui porte une créance ou une affectation, laisse `reimbursement_offset` et les créances incohérents (passer par le mode API).

---

## 🔑 Connexion de Claude Code (recommandé)

En production, `docker-compose.prod.yml` lance `mcp-server` (mode API, transport `streamable-http`, sans état) ; Nginx l'expose sur `https://<domaine>/mcp`. Aucun port publié, aucun secret dans le conteneur.

1. Numera → **Paramètres → Compte → Claude Code (MCP)** → **Générer un token** (`nmr_…`, affiché une seule fois).
2. Lancer la commande affichée :
   ```bash
   claude mcp add --transport http --scope user numera https://<domaine>/mcp \
     --header "Authorization: Bearer nmr_…"
   ```
3. `claude mcp list` doit afficher `numera` connecté.

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
- **Périmètre** : un token MCP a les droits de l'admin sur les données, mais **aucun accès à `/admin`** (profil, mot de passe, reset de la base, gestion des tokens) : 403.
- **Transport** : le token circule dans un en-tête ; en production, n'exposer Numera qu'en HTTPS.
- **Mode SQLite** : stdio uniquement (refuse de démarrer en HTTP) ; lecture via connexion `mode=ro` ; SQL brut limité aux `SELECT` (mots-clés `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `REPLACE`, `ATTACH`, `DETACH`, `PRAGMA` refusés), `LIMIT 200` forcé ; écritures par outils validés uniquement ; journal WAL pour cohabiter avec le backend.
- Les écritures de l'agent (ajout, suppression, catégorisation en masse) modifient vraiment les données : faire une sauvegarde (`make backup-now`) avant une session de nettoyage en masse.
- Logs sur stderr.

Tests : `cd mcp-server && python3 -m pytest test_server_auth.py -q` (middleware) et `backend/tests/test_mcp_tokens.py` (tokens côté API).

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
├── server_api.py      # Mode proxy API (httpx, token MCP)
├── server_auth.py     # Validation des tokens par l'API (transports HTTP)
├── server_sqlite.py   # Mode SQLite direct
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```
