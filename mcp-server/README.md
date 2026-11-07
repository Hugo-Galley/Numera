# 🔌 MCP server — Numera

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that lets Claude (Claude Code, Claude Desktop) query the budget-tracking data, **read-only**.

The server is a **proxy of the FastAPI API**: it calls the API with an **MCP token** generated in Numera and reuses the KPIs computed by the backend (exposed on `/mcp` by Nginx). **48 tools, 4 resources, 6 prompts.** The entry point is `server.py`, the code lives in the `numera_mcp/` package (see [Structure](#-structure)).

> Project rule: KPIs are computed by the backend. The MCP server has no direct database access and recomputes nothing.

---

## 🧰 Tools

**Read-only.** No tool creates, modifies or deletes data, and the API guarantees it too: with an MCP token, any request other than `GET` receives a 403 (`Accès MCP en lecture seule`, "MCP access is read-only"). Changes are made in the Numera interface.

**Data**
`list_accounts`, `list_categories`, `list_transactions`, `get_transaction`, `search_transactions`, `list_merchants`, `list_recurring_transactions`, `list_savings_goals`, `list_provisions`, `list_benefits`, `list_financial_events`, `list_tags`, `list_transfer_rules`, `list_reimbursement_claims`

**Analyses (via `/analytics/*`)**
`get_budget_summary`, `get_expenses_by_category`, `get_top_merchants`, `get_subscriptions`, `get_budget_alerts`, `get_insights`, `get_monthly_report`, `get_budget_period`, `get_resilience`, `get_month_review`, `get_wrapped`, `list_month_closures`, `get_kpi_history`, `get_cashflow_projection`, `get_wealth_forecast`, `get_fire_projection`, `get_money_flow`, `get_tax_overview`, `get_work_time`

**Investments**
`get_portfolio`, `get_dividends`, `list_holdings`, `list_investment_transactions`, `list_etf_profiles`, `get_etf_profile`, `get_investments_summary`, `get_investment_performance` (gains, zero-point baseline, average cost), `get_investment_performance_history`, `get_investments_allocation`, `get_investments_allocation_advanced`, `get_patrimoine_allocation`, `get_diversity_scanner`

**Resources**: `data://accounts`, `data://categories`, `data://tags`, `data://recurring-transactions`

**Prompts**: `analyze_month`, `audit_subscriptions`, `budget_review`, `categorize_uncategorized` (suggests categories, to be applied in the interface), `analyze_portfolio`, `analyze_etf_lookthrough`

---

## 🔑 Connecting Claude (Code / Desktop)

In production, `infra/docker-compose.prod.yml` starts `mcp-server` (`streamable-http` transport, stateless); Nginx exposes it on `https://<domain>/mcp`. No published port, no secret in the container.

1. Numera → **Settings → Security → Claude (MCP)** (French UI: *Paramètres → Sécurité*) → **Generate a token** (`nmr_…`, shown only once).
2. Run the displayed command:
   ```bash
   claude mcp add --transport http --scope user numera https://<domain>/mcp \
     --header "Authorization: Bearer nmr_…"
   ```
3. `claude mcp list` must show `numera` as connected.

### Claude Desktop

Claude Desktop cannot send an `Authorization` header to a remote server (its "custom connectors" expect OAuth). So we go through the local [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) bridge (**Node.js required**). The interface generates the block to merge into `claude_desktop_config.json` (Settings → Developer → Edit config; macOS: `~/Library/Application Support/Claude/`):

```json
{
  "mcpServers": {
    "numera": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://<domain>/mcp", "--header", "Authorization:${NUMERA_AUTH}"],
      "env": { "NUMERA_AUTH": "Bearer nmr_…" }
    }
  }
}
```

The token goes through the environment variable (`Authorization:${NUMERA_AUTH}` with no space: works around an argument-escaping bug in Claude Desktop). Restart Claude Desktop afterwards.

Authentication chain:

```
Claude Code ──Bearer nmr_…──▶ Nginx /mcp ──▶ mcp-server
   numera_mcp/auth.py: GET /auth/whoami with this token (401 otherwise, validation cached for 30 s)
   each tool     : API call with the same token (numera_mcp.api_client.APIClient)
backend: get_current_user accepts the token (SHA-256 fingerprint in mcp_tokens),
         refuses it if revoked or if MCP access is switched off, and /admin always refuses it (403)
```

Revoking a token or switching off "Accès MCP" ("MCP access") takes effect immediately for data: tool calls are refused by the API, even during the 30 s in which the middleware validation is cached.

In dev (`make dev`), the `mcp-server` service listens on `8100` and Vite proxies `/mcp`: the command displayed by the interface (`http://localhost:5173/mcp`) works as is.

---

## 📦 Local installation (stdio)

Prerequisite: Python 3.12+.

```bash
cd mcp-server
uv sync                             # mcp[cli]>=1.9.0 (httpx comes with mcp), pinned by uv.lock

# Test with the MCP Inspector
npx -y @modelcontextprotocol/inspector uv run python server.py
```

## ⚙️ Environment variables

| Variable | Scope | Description | Default |
|----------|-------|-------------|---------|
| `MCP_SERVER_NAME` | all | Displayed name | `Numera` |
| `MCP_TRANSPORT` | all | `stdio`, `streamable-http`, `sse` | `stdio` (the Docker image sets `streamable-http`) |
| `MCP_HOST` / `MCP_PORT` | HTTP/SSE | Listening address | `127.0.0.1` / `8100` (the Docker image sets `0.0.0.0`) |
| `MCP_API_URL` | all | API URL: `http://backend:8001` in Docker, `https://domain/api` through Nginx | `http://localhost:8001` (the Docker image sets `http://backend:8001`) |
| `MCP_API_TOKEN` | stdio | MCP token generated in the interface — **required in stdio**. In HTTP, ignored: each client sends its own | — |

No more passwords: `MCP_API_USERNAME`, `MCP_API_PASSWORD` and `MCP_AUTH_TOKEN` no longer exist.

### Local stdio client (optional)

For example for Claude Code without going through `/mcp`:

```bash
claude mcp add --scope user numera-local \
  -e MCP_API_URL=https://<domain>/api -e MCP_API_TOKEN=nmr_… \
  -- python3 /absolute/path/numera/mcp-server/server.py
```

---

## 🐳 Docker

`mcp-server` service of `infra/docker-compose.prod.yml` (always started, the Nginx frontend depends on it): `streamable-http` on `8100` inside the Docker network only, `MCP_API_URL=http://backend:8001`. Nginx block: `location = /mcp` in `frontend/nginx.conf` (`proxy_buffering off` for the SSE stream).

The server is built with `stateless_http` (no session affinity) and without the `mcp` library's DNS-rebinding protection (it only accepts `Host: localhost`, which breaks behind Nginx; unnecessary since access relies on an explicit bearer token).

Manual build: `docker build -t numera-mcp ./mcp-server`.

---

## 🔒 Security

- **MCP tokens**: 256 random bits prefixed `nmr_`, only the SHA-256 fingerprint is stored (`mcp_tokens`), shown only once, revocable one by one, `last_used_at` updated (at most once a minute). Global "Accès MCP" switch (`system_settings.mcp_enabled`).
- **Scope**: an MCP token is **read-only** (`GET` only, 403 otherwise) and has **no access to `/admin`** (profile, password, database reset, token management).
- **Transport**: the token travels in a header; in production, only expose Numera over HTTPS.
- Logs on stderr.

Tests: `cd mcp-server && uv run --with pytest python -m pytest tests -q` (frozen MCP surface, authentication middleware, read-only, HTTP transport) and `backend/tests/systeme/test_mcp_tokens.py` (tokens on the API side).

---

## 🧪 Examples

- "Analyse my May 2026 budget" → `get_budget_summary`, `get_expenses_by_category`, `get_top_merchants` (or the `analyze_month` prompt).
- "Audit my subscriptions" → `audit_subscriptions` prompt (`get_subscriptions`).
- "How much at Amazon this year?" → `search_transactions`.
- "Analyse my portfolio" → `analyze_portfolio` / `analyze_etf_lookthrough` prompts.

---

## 📁 Structure

```
mcp-server/
├── server.py              # Entry point (stdio or HTTP + authentication middleware)
├── numera_mcp/
│   ├── config.py          # Environment variables, transport, logs
│   ├── auth.py            # Token validation by the API (HTTP transports)
│   ├── api_client.py      # Read-only HTTP client (GET) + API error handling
│   ├── formatting.py      # serialize, format_table
│   ├── budget_period.py   # Current budget month
│   ├── resources.py       # data://… resources
│   ├── prompts.py         # Analysis prompts
│   ├── app.py             # Assembly: module registration, HTTP application
│   └── tools/             # One module per backend domain, each exposes register(mcp)
│       ├── budget.py, budget_revue.py        # transactions, categories, merchants, month review…
│       ├── comptes.py                        # accounts, loans, financial events
│       ├── investissement.py, etf.py         # portfolio, positions, dividends, ETFs
│       └── analytics.py, projections.py      # budget, KPIs, projections, flows, net worth
├── tests/                 # frozen MCP surface (snapshot), auth, read-only, HTTP transport
├── ruff.toml
├── pyproject.toml         # Dependencies (uv)
├── uv.lock
├── Dockerfile
├── .env.example
└── README.md
```

Adding a tool: a function in the domain module, add it to its `TOOLS` list, then regenerate the `tests/` snapshot after review (`tests/surface_snapshot.json`).
