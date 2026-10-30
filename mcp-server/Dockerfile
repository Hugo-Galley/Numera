FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159

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

# Mode API derrière Nginx (/mcp) : aucun secret, les tokens des clients sont validés par l'API
ENV MCP_MODE=api
ENV MCP_API_URL=http://backend:8001
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8100
ENV MCP_SERVER_NAME="Numera"

EXPOSE 8100

CMD ["python", "server.py"]
