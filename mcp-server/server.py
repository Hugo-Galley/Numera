"""
🔌 MCP Server Dispatcher — Suivi Budget
======================================
Permet d'exécuter le serveur MCP dans l'un des deux modes :
1. Mode SQLite Direct (server_sqlite.py) : Requêtes directes à la base de données.
2. Mode API Proxy (server_api.py) : Requêtes HTTP vers l'API FastAPI du VPS.

Détection automatique :
- Si MCP_MODE est défini à "api" ou "sqlite", ce mode est forcé.
- Si MCP_API_URL est défini, le mode API Proxy est activé.
- Sinon, si le fichier SQLite à MCP_DB_PATH existe, le mode SQLite Direct est activé.
- Sinon, le mode API Proxy est activé par défaut.
"""

import os
import sys
import runpy

# ─── Détection du mode ────────────────────────────────────────────────────────

mode = os.environ.get("MCP_MODE", "").lower()

if mode not in ("api", "sqlite"):
    api_url = os.environ.get("MCP_API_URL")
    db_path = os.environ.get("MCP_DB_PATH")
    
    if not db_path:
        db_path = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "suivi_budget.db")
    
    db_exists = os.path.exists(os.path.abspath(db_path))
    
    if api_url:
        mode = "api"
    elif db_exists:
        mode = "sqlite"
    else:
        # Fallback par défaut
        mode = "api"

# Déterminer le fichier cible
dir_path = os.path.dirname(os.path.abspath(__file__))
if mode == "api":
    target_path = os.path.join(dir_path, "server_api.py")
else:
    target_path = os.path.join(dir_path, "server_sqlite.py")

# Ajouter le répertoire parent au sys.path pour les imports
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

# ─── Dispatching ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🔌 MCP Dispatcher: Mode détecté = '{mode.upper()}'", file=sys.stderr)
    print(f"📂 Cible : {target_path}", file=sys.stderr)
    runpy.run_path(target_path, run_name="__main__")
else:
    # Si le module est importé (ex: par l'inspecteur MCP ou la CLI),
    # on exécute la cible dans le même namespace pour exporter 'mcp' et ses outils.
    globals().update(runpy.run_path(target_path, run_name=__name__))
