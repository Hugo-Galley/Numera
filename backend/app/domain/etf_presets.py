"""Profils ETF système, chargés depuis `etf_presets.json` : des identifiants (nom, ticker, ISIN, alias) seulement.

Aucune composition n'est codée en dur : elle est lue chez l'émetteur (cf. `services/investissement/etf_composition.py`).
"""

import json
from pathlib import Path

SYSTEM_ETF_PRESETS: list[dict[str, str | list[str]]] = json.loads(
    Path(__file__).with_name("etf_presets.json").read_text(encoding="utf-8"))
