# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

# Étape de build : compilateur et uv n'atteignent jamais l'image finale
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS builder

COPY --from=uv /uv /usr/local/bin/uv
# uv : environnement figé par uv.lock, hors de /app pour ne pas être masqué par les volumes
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Image finale : interpréteur, git (sauvegarde vers GitHub), venv et code, rien d'autre
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

LABEL org.opencontainers.image.title="Numera backend" \
      org.opencontainers.image.licenses="MIT"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp

# Utilisateur non-root (UID 1000 : celui du premier utilisateur Linux, pour les volumes ./data et ./backups)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 numera \
    && useradd --uid 1000 --gid numera --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin numera \
    && mkdir -p /app/data /app/backups \
    && chown -R numera:numera /app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=numera:numera . /app

USER numera

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=4)"]
