"""Régénère `surface_snapshot.json` : à lancer volontairement après avoir ajouté ou modifié un outil.

    cd mcp-server && MCP_API_TOKEN=x python -m tests.regen_snapshot
"""
import json
from pathlib import Path

from server import mcp
from tests.surface import describe

path = Path(__file__).parent / "surface_snapshot.json"
path.write_text(json.dumps(describe(mcp), indent=1, ensure_ascii=False, sort_keys=True) + "\n")
print(f"{path} mis à jour")
