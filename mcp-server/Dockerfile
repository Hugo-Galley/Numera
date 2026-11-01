# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv

FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913 AS builder

COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

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
