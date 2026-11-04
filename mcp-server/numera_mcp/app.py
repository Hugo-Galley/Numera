"""Assemblage du serveur MCP : enregistrement des outils, ressources et prompts, application HTTP."""
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from numera_mcp import prompts, resources
from numera_mcp.config import SERVER_NAME, TRANSPORT
from numera_mcp.tools import analytics, budget, budget_revue, comptes, etf, investissement, projections

mcp = MCPServer(SERVER_NAME)

for module in (resources, budget, budget_revue, comptes, investissement, etf, analytics, projections, prompts):
    module.register(mcp)


def http_app():
    """Application ASGI du transport HTTP configuré (avant le middleware d'authentification)."""
    # La protection DNS rebinding n'autorise que localhost ; derrière Nginx, l'hôte est le domaine public.
    # Inutile ici : l'accès repose sur un token bearer explicite, pas sur un accès réseau local.
    security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    if TRANSPORT == "streamable-http":
        # Sans état : chaque requête HTTP est autonome (pas d'affinité de session derrière Nginx)
        return mcp.streamable_http_app(stateless_http=True, transport_security=security)
    return mcp.sse_app(transport_security=security)
