# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.13.8@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 AS uv

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS builder

COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

LABEL maintainer="Hugo Galley" \
      description="Serveur MCP pour Suivi Budget" \
      org.opencontainers.image.title="Numera MCP" \
      org.opencontainers.image.licenses="MIT"

# Empêcher Python de buffer stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# zlib1g : l'image de base peut retarder sur les correctifs de sécurité Debian (CVE-2026-76844, CVE-2026-85091) ;
# la mise à niveau ciblée est sans effet une fois le digest de base à jour.
RUN apt-get update && apt-get install -y --no-install-recommends --only-upgrade zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Utilisateur non-root pour la sécurité
RUN groupadd --gid 1000 mcp && useradd --uid 1000 --gid mcp --no-create-home --shell /usr/sbin/nologin mcp

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY server.py ./
COPY numera_mcp ./numera_mcp

USER mcp

# Derrière Nginx (/mcp) : aucun secret, les tokens des clients sont validés par l'API
ENV MCP_API_URL=http://backend:8001 \
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8100 \
    MCP_SERVER_NAME="Numera"

EXPOSE 8100

# Le port répond (le endpoint /mcp exige un token : on teste seulement l'ouverture du socket)
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import socket; socket.create_connection(('127.0.0.1', 8100), 3).close()"]

CMD ["python", "server.py"]
