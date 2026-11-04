"""Non-régression : la surface MCP (outils, schémas, ressources, prompts) ne change pas lors d'un refactor.

Mettre à jour le snapshot volontairement : `python -m tests.regen_snapshot` (depuis mcp-server/).
"""
import json
import os
from pathlib import Path

os.environ.setdefault("MCP_API_TOKEN", "nmr_test")

from tests.surface import describe

SNAPSHOT = json.loads((Path(__file__).parent / "surface_snapshot.json").read_text())


def _surface():
    from server import mcp
    return describe(mcp)


def test_tool_names_are_frozen():
    assert len(SNAPSHOT["tools"]) == 48
    assert sorted(_surface()["tools"]) == sorted(SNAPSHOT["tools"])


def test_tool_signatures_and_descriptions_are_frozen():
    surface = _surface()["tools"]
    for name, expected in SNAPSHOT["tools"].items():
        assert surface[name] == expected, name


def test_resources_and_prompts_are_frozen():
    surface = _surface()
    assert surface["resources"] == SNAPSHOT["resources"]
    assert surface["prompts"] == SNAPSHOT["prompts"]
