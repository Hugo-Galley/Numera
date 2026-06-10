FROM python:3.12-slim

LABEL maintainer="Hugo Galley"
LABEL description="Serveur MCP pour Suivi Budget"

# Empêcher Python de buffer stdout/stderr
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le serveur
COPY server*.py ./

# Créer un utilisateur non-root pour la sécurité
RUN groupadd -r mcp && useradd -r -g mcp mcp
USER mcp

# Le volume de la DB sera monté ici
VOLUME ["/data"]

# Variables d'environnement par défaut
ENV MCP_DB_PATH=/data/suivi_budget.db
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8100
ENV MCP_SERVER_NAME="Suivi Budget MCP"

EXPOSE 8100

CMD ["python", "server.py"]
