"""Fiche d'un ETF : répartitions d'un fonds en % (sans base), avec les mêmes postes que le scanner de diversification."""
import json
from collections.abc import Sequence

from app.domain.diversity import spread_lines, spread_weights
from app.domain.etf_composition import EtfLine


def _sorted(weights: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(((name, round(weight, 4)) for name, weight in weights.items()), key=lambda kv: -kv[1])


def aggregate_weights(lines: Sequence[EtfLine], attribute: str) -> list[tuple[str, float]]:
    """(pays ou secteur, % du fonds) calculés ligne à ligne, décroissants."""
    weights: dict[str, float] = {}
    spread_lines(weights, lines, attribute, 100.0)
    return _sorted(weights)


def stored_weights(raw: str) -> list[tuple[str, float]]:
    """Même chose depuis les agrégats enregistrés sur un profil ; vide si le profil n'en a aucun."""
    try:
        if not json.loads(raw or "{}"):
            return []
    except ValueError:
        return []
    weights: dict[str, float] = {}
    spread_weights(weights, raw, 100.0)
    return _sorted(weights)


def exposure_eur(weight: object, held_value_eur: float) -> float:
    """Exposition en € d'une ligne : son poids (% du fonds) × la valeur détenue ; 0 si le poids n'est pas un nombre."""
    if isinstance(weight, bool) or not isinstance(weight, int | float):
        return 0.0
    return round(weight / 100 * held_value_eur, 2)
