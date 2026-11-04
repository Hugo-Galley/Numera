"""Client HTTP en lecture seule de l'API Numera et gestion de ses erreurs."""
import httpx

from numera_mcp.auth import current_token
from numera_mcp.config import API_BASE_URL, API_TOKEN, HTTP_TRANSPORTS, TRANSPORT


class APIClient:
    """Client HTTP en lecture seule (GET) de l'API, authentifié par le token MCP (celui du client en HTTP, MCP_API_TOKEN en stdio)."""

    def __init__(self, base_url: str, static_token: str | None):
        self.base_url = base_url.rstrip("/")
        self._static_token = static_token
        self._client = httpx.Client(timeout=30.0)

    def _token(self) -> str:
        if self._static_token:
            return self._static_token
        # Transport HTTP : le middleware a déjà validé le token de la requête en cours et l'a déposé ici
        token = current_token.get()
        if not token:
            raise PermissionError("Aucun token MCP dans la requête")
        return token

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{path}"
        try:
            return self._client.request(method, url, headers={"Authorization": f"Bearer {self._token()}"}, **kwargs)
        except httpx.ConnectError as e:
            raise ConnectionError(
                f"❌ Impossible de joindre l'API ({self.base_url}). Vérifiez MCP_API_URL."
            ) from e

    def get(self, path: str, params: dict | None = None) -> httpx.Response:
        return self._request("GET", path, params=params)

    def close(self):
        self._client.close()




api = APIClient(API_BASE_URL, API_TOKEN if TRANSPORT not in HTTP_TRANSPORTS else None)


def handle_response(resp: httpx.Response, label: str = "") -> str:
    """Gère la réponse API et retourne un message formaté."""
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return f"❌ Erreur API ({resp.status_code}) : {detail}"
    return ""

