"""Description sérialisable de la surface MCP exposée (outils, ressources, prompts)."""
import asyncio


def describe(mcp) -> dict:
    async def collect():
        return await mcp.list_tools(), await mcp.list_resources(), await mcp.list_prompts()

    tools, resources, prompts = asyncio.run(collect())
    return {
        "tools": {
            t.name: {"description": t.description, "inputSchema": t.input_schema}
            for t in sorted(tools, key=lambda t: t.name)
        },
        "resources": {str(r.uri): {"name": r.name, "description": r.description} for r in sorted(resources, key=lambda r: str(r.uri))},
        "prompts": {
            p.name: {"description": p.description, "arguments": [a.model_dump() for a in (p.arguments or [])]}
            for p in sorted(prompts, key=lambda p: p.name)
        },
    }
