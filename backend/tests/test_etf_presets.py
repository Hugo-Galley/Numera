"""Préréglages des profils ETF système (`domain/etf_presets.json`)."""
from app.domain.etf_presets import SYSTEM_ETF_PRESETS


def test_presets_shape():
    assert len(SYSTEM_ETF_PRESETS) == 10
    assert len({p["name"] for p in SYSTEM_ETF_PRESETS}) == 10
    for preset in SYSTEM_ETF_PRESETS:
        assert {"name", "ticker", "isin", "aliases", "countries", "sectors", "top_holdings"} <= preset.keys()
