"""Constantes du modèle de sur-exposition : valeurs fixées par la spec, en un seul endroit."""
from app.domain.exposure import params


def test_model_constants():
    assert params.HISTORY_WEEKS == 104
    assert params.MIN_HISTORY_WEEKS == 52
    assert params.SAME_EXPOSURE_MAX_TRACKING_ERROR == 0.02
    assert params.SAME_EXPOSURE_MIN_SIMILARITY == 0.95
    assert params.BLOCK_CORRELATION == 0.8
    assert params.OVERWEIGHT_RATIO == 1.5
    assert params.OVERWEIGHT_MIN_POINTS == 5.0
    assert params.DEFAULT_MARKET_INDEX == "MSCI ACWI"
