"""Point d'entrée du serveur MCP Numera (lecture seule, proxy de l'API FastAPI).

  [Claude Code] ←HTTPS (streamable-http)→ [Nginx /mcp] → [serveur MCP] ←HTTP→ [API]
  [Client local] ←stdio→ [serveur MCP] ←HTTP→ [API]

Authentification par token MCP généré dans Numera (Paramètres → Sécurité) : en HTTP, celui du client
(validé par le backend, `numera_mcp/auth.py`) ; en stdio, `MCP_API_TOKEN`. Voir `README.md`.
"""
from numera_mcp import __version__
from numera_mcp.app import http_app, mcp
from numera_mcp.config import API_BASE_URL, HOST, HTTP_TRANSPORTS, PORT, SERVER_NAME, TRANSPORT, logger


def main() -> None:
    logger.info(f"Démarrage du serveur MCP '{SERVER_NAME}' v{__version__}")
    logger.info(f"API cible : {API_BASE_URL}")
    logger.info(f"Transport : {TRANSPORT}")

    if TRANSPORT in HTTP_TRANSPORTS:
        import uvicorn

        from numera_mcp.auth import protect

        logger.info(f"Écoute sur {HOST}:{PORT} (tokens MCP validés par l'API)")
        uvicorn.run(
            protect(http_app(), API_BASE_URL), host=HOST, port=PORT, proxy_headers=True, forwarded_allow_ips="*"
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
