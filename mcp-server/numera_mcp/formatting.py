"""Mise en forme des réponses renvoyées au LLM."""
import json
from typing import Any


def serialize(obj: Any) -> str:
    """Sérialise en JSON lisible."""
    return json.dumps(obj, indent=2, default=str, ensure_ascii=False)


def format_table(rows: list[dict], max_col_width: int = 40) -> str:
    """Formate des résultats en table lisible."""
    if not rows:
        return "Aucun résultat."

    columns = list(rows[0].keys())
    widths = {}
    for col in columns:
        values = [str(row.get(col, "")) for row in rows]
        widths[col] = min(max(len(col), max(len(v) for v in values)), max_col_width)

    header = " | ".join(col.ljust(widths[col])[:widths[col]] for col in columns)
    separator = "-+-".join("-" * widths[col] for col in columns)
    lines = [header, separator]
    for row in rows:
        line = " | ".join(
            str(row.get(col, "")).ljust(widths[col])[:widths[col]]
            for col in columns
        )
        lines.append(line)
    return "\n".join(lines)
