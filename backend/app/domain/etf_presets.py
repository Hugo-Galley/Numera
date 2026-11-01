"""Profils ETF système : compositions de repli (pays, secteurs, top 10), chargées depuis `etf_presets.json`.

Ces valeurs ne servent que tant que Yahoo ne fournit pas le champ et que l'utilisateur ne l'a pas saisi
(cf. `composition_sources`).
"""

import json
from pathlib import Path
from typing import Any

SYSTEM_ETF_PRESETS: list[dict[str, Any]] = json.loads((Path(__file__).with_name("etf_presets.json")).read_text(encoding="utf-8"))
