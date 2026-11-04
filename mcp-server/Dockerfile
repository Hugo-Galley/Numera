# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS builder

COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159

LABEL maintainer="Hugo Galley" \
      description="Serveur MCP pour Suivi Budget" \
      org.opencontainers.image.title="Numera MCP" \
      org.opencontainers.image.licenses="MIT"

# Empêcher Python de buffer stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Utilisateur non-root pour la sécurité
RUN groupadd --gid 1000 mcp && useradd --uid 1000 --gid mcp --no-create-home --shell /usr/sbin/nologin mcp

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY server*.py ./

USER mcp

# Mode API derrière Nginx (/mcp) : aucun secret, les tokens des clients sont validés par l'API
ENV MCP_MODE=api \
    MCP_API_URL=http://backend:8001 \
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8100 \
    MCP_SERVER_NAME="Numera"

EXPOSE 8100

# Le port répond (le endpoint /mcp exige un token : on teste seulement l'ouverture du socket)
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import socket; socket.create_connection(('127.0.0.1', 8100), 3).close()"]

CMD ["python", "server.py"]
