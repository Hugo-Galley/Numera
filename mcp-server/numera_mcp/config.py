"""Configuration du serveur MCP : variables d'environnement, transport, journalisation."""
import logging
import os

# URL de base de l'API (dans Docker : http://backend:8001)
API_BASE_URL = os.environ.get("MCP_API_URL", "http://localhost:8001")

SERVER_NAME = os.environ.get("MCP_SERVER_NAME", "Numera")

# Transport (stdio par défaut pour usage local)
TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")
HOST = os.environ.get("MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_PORT", "8100"))
HTTP_TRANSPORTS = ("sse", "streamable-http")

# stdio uniquement : token MCP généré dans l'interface (en HTTP, c'est celui du client)
API_TOKEN = os.environ.get("MCP_API_TOKEN")
if TRANSPORT not in HTTP_TRANSPORTS and not API_TOKEN:
    raise ValueError(
        "MCP_API_TOKEN doit être défini en transport stdio : générez un token dans Numera (Paramètres → Sécurité)"
    )

# Logging (sur stderr pour ne pas interférer avec stdio)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mcp-suivi-budget")
