# 🔌 Serveur MCP — Numera

Serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) permettant à Claude (Claude Code, Claude Desktop) d'interroger les données du suivi budgétaire, **en lecture seule**.

Le serveur est un **proxy de l'API FastAPI** : il appelle l'API avec un **token MCP** généré dans Numera et reprend les KPI calculés par le backend (exposé sur `/mcp` par Nginx). **48 outils, 4 ressources, 6 prompts.** Le point d'entrée est `server.py`, le code vit dans le package `numera_mcp/` (voir [Structure](#-structure)).

> Règle du projet : les KPI sont calculés par le backend. Le serveur MCP n'a pas d'accès direct à la base et ne recalcule rien.

---

## 🧰 Outils

**Lecture seule.** Aucun outil ne crée, modifie ou supprime de données, et l'API le garantit aussi : avec un token MCP, toute requête autre que `GET` reçoit un 403 (`Accès MCP en lecture seule`). Les modifications se font dans l'interface Numera.

**Données**
`list_accounts`, `list_categories`, `list_transactions`, `get_transaction`, `search_transactions`, `list_merchants`, `list_recurring_transactions`, `list_savings_goals`, `list_provisions`, `list_benefits`, `list_financial_events`, `list_tags`, `list_transfer_rules`, `list_reimbursement_claims`

**Analyses (via `/analytics/*`)**
`get_budget_summary`, `get_expenses_by_category`, `get_top_merchants`, `get_subscriptions`, `get_budget_alerts`, `get_insights`, `get_monthly_report`, `get_budget_period`, `get_resilience`, `get_month_review`, `get_wrapped`, `list_month_closures`, `get_kpi_history`, `get_cashflow_projection`, `get_wealth_forecast`, `get_fire_projection`, `get_money_flow`, `get_tax_overview`, `get_work_time`

**Investissements**
`get_portfolio`, `get_dividends`, `list_holdings`, `list_investment_transactions`, `list_etf_profiles`, `get_etf_profile`, `get_investments_summary`, `get_investment_performance` (gains, baseline point zéro, PRU), `get_investment_performance_history`, `get_investments_allocation`, `get_investments_allocation_advanced`, `get_patrimoine_allocation`, `get_diversity_scanner`

**Ressources** : `data://accounts`, `data://categories`, `data://tags`, `data://recurring-transactions`

**Prompts** : `analyze_month`, `audit_subscriptions`, `budget_review`, `categorize_uncategorized` (propose des catégories, à appliquer dans l'interface), `analyze_portfolio`, `analyze_etf_lookthrough`

---

## 🔑 Connexion de Claude (Code / Desktop)

En production, `docker-compose.prod.yml` lance `mcp-server` (transport `streamable-http`, sans état) ; Nginx l'expose sur `https://<domaine>/mcp`. Aucun port publié, aucun secret dans le conteneur.

1. Numera → **Paramètres → Sécurité → Claude (MCP)** → **Générer un token** (`nmr_…`, affiché une seule fois).
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
   numera_mcp/auth.py : GET /auth/whoami avec ce token (refus 401 sinon, validation gardée 30 s)
   chaque outil   : appel API avec ce même token (numera_mcp.api_client.APIClient)
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
uv sync                             # mcp[cli]>=1.9.0 (httpx arrive avec mcp), figé par uv.lock

# Tester avec l'Inspector MCP
npx -y @modelcontextprotocol/inspector uv run python server.py
```

## ⚙️ Variables d'environnement

| Variable | Portée | Description | Défaut |
|----------|--------|-------------|--------|
| `MCP_SERVER_NAME` | tous | Nom affiché | `Numera` |
| `MCP_TRANSPORT` | tous | `stdio`, `streamable-http`, `sse` | `stdio` (l'image Docker met `streamable-http`) |
| `MCP_HOST` / `MCP_PORT` | HTTP/SSE | Écoute | `127.0.0.1` / `8100` (l'image Docker met `0.0.0.0`) |
| `MCP_API_URL` | tous | URL de l'API : `http://backend:8001` dans Docker, `https://domaine/api` via Nginx | `http://localhost:8001` (l'image Docker met `http://backend:8001`) |
| `MCP_API_TOKEN` | stdio | Token MCP généré dans l'interface — **obligatoire en stdio**. En HTTP, ignoré : chaque client envoie le sien | — |

Plus aucun mot de passe : `MCP_API_USERNAME`, `MCP_API_PASSWORD` et `MCP_AUTH_TOKEN` n'existent plus.

### Client local en stdio (optionnel)

Par exemple pour Claude Code sans passer par `/mcp` :

```bash
claude mcp add --scope user numera-local \
  -e MCP_API_URL=https://<domaine>/api -e MCP_API_TOKEN=nmr_… \
  -- python3 /chemin/absolu/numera/mcp-server/server.py
```

---

## 🐳 Docker

Service `mcp-server` de `docker-compose.prod.yml` (toujours lancé, frontend Nginx en dépend) : `streamable-http` sur `8100` dans le réseau Docker seulement, `MCP_API_URL=http://backend:8001`. Bloc Nginx : `location = /mcp` dans `frontend/nginx.conf` (`proxy_buffering off` pour le flux SSE).

Le serveur est construit en `stateless_http` (pas d'affinité de session) et sans protection DNS rebinding de la lib `mcp` (elle n'accepte que `Host: localhost`, ce qui casse derrière Nginx ; inutile puisque l'accès repose sur un token bearer explicite).

Build manuel : `docker build -t numera-mcp ./mcp-server`.

---

## 🔒 Sécurité

- **Tokens MCP** : 256 bits aléatoires préfixés `nmr_`, seule l'empreinte SHA-256 est stockée (`mcp_tokens`), affichés une seule fois, révocables un par un, `last_used_at` mis à jour (au plus une fois par minute). Interrupteur global « Accès MCP » (`system_settings.mcp_enabled`).
- **Périmètre** : un token MCP est en **lecture seule** (`GET` uniquement, 403 sinon) et n'a **aucun accès à `/admin`** (profil, mot de passe, reset de la base, gestion des tokens).
- **Transport** : le token circule dans un en-tête ; en production, n'exposer Numera qu'en HTTPS.
- Logs sur stderr.

Tests : `cd mcp-server && uv run --with pytest python -m pytest tests -q` (surface MCP figée, middleware d'authentification, lecture seule, transport HTTP) et `backend/tests/systeme/test_mcp_tokens.py` (tokens côté API).

---

## 🧪 Exemples

- « Analyse mon budget de mai 2026 » → `get_budget_summary`, `get_expenses_by_category`, `get_top_merchants` (ou prompt `analyze_month`).
- « Audit de mes abonnements » → prompt `audit_subscriptions` (`get_subscriptions`).
- « Combien chez Amazon cette année ? » → `search_transactions`.
- « Analyse mon portefeuille » → prompts `analyze_portfolio` / `analyze_etf_lookthrough`.

---

## 📁 Structure

```
mcp-server/
├── server.py              # Point d'entrée (stdio ou HTTP + middleware d'authentification)
├── numera_mcp/
│   ├── config.py          # Variables d'environnement, transport, logs
│   ├── auth.py            # Validation des tokens par l'API (transports HTTP)
│   ├── api_client.py      # Client HTTP en lecture seule (GET) + gestion des erreurs API
│   ├── formatting.py      # serialize, format_table
│   ├── budget_period.py   # Mois budgétaire courant
│   ├── resources.py       # Ressources data://…
│   ├── prompts.py         # Prompts d'analyse
│   ├── app.py             # Assemblage : enregistrement des modules, application HTTP
│   └── tools/             # Un module par domaine du backend, chacun expose register(mcp)
│       ├── budget.py, budget_revue.py        # transactions, catégories, marchands, revue de mois…
│       ├── comptes.py                        # comptes, prêts, événements financiers
│       ├── investissement.py, etf.py         # portefeuille, positions, dividendes, ETF
│       └── analytics.py, projections.py      # budget, KPI, projections, flux, patrimoine
├── tests/                 # surface MCP figée (snapshot), auth, lecture seule, transport HTTP
├── ruff.toml
├── pyproject.toml         # Dépendances (uv)
├── uv.lock
├── Dockerfile
├── .env.example
└── README.md
```

Ajouter un outil : une fonction dans le module du domaine, l'ajouter à sa liste `TOOLS`, puis régénérer le snapshot de `tests/` après revue (`tests/surface_snapshot.json`).
