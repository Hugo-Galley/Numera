FROM ghcr.io/astral-sh/uv:0.11.21@sha256:ff07b86af50d4d9391d9daf4ff89ce427bc544f9aae87057e69a1cc0aa369946 AS uv

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159

LABEL maintainer="Hugo Galley"
LABEL description="Serveur MCP pour Suivi Budget"

# Empêcher Python de buffer stdout/stderr
ENV PYTHONUNBUFFERED=1

COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Installer les dépendances
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copier le serveur
COPY server*.py ./

# Créer un utilisateur non-root pour la sécurité
RUN groupadd -r mcp && useradd -r -g mcp mcp
USER mcp

# Mode API derrière Nginx (/mcp) : aucun secret, les tokens des clients sont validés par l'API
ENV MCP_MODE=api
ENV MCP_API_URL=http://backend:8001
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8100
ENV MCP_SERVER_NAME="Numera"

EXPOSE 8100

CMD ["python", "server.py"]
