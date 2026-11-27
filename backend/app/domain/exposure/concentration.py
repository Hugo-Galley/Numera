"""Concentration d'un portefeuille : nombre de paris indépendants et blocs de lignes corrélées (calculs purs).

`N_eff = 1 / Σᵢ Σⱼ wᵢ · wⱼ · ρᵢⱼ` généralise l'inverse du HHI : des lignes indépendantes donnent `1 / Σ w²`, des lignes
qui bougent toutes ensemble donnent 1. Une corrélation inconnue (`None`) ou négative compte 0, la diagonale vaut 1."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.exposure.params import BLOCK_CORRELATION


@dataclass(frozen=True)
class Block:
    """Groupe d'au moins deux expositions corrélées : membres, poids total (% du portefeuille), ρ moyen entre membres."""

    keys: tuple[str, ...]
    weight_pct: float
    mean_rho: float


def _clean_rho(rho: Sequence[Sequence[float | None]], i: int, j: int) -> float:
    """ρ utilisable : 1 sur la diagonale, 0 si inconnu ou négatif."""
    if i == j:
        return 1.0
    value = rho[i][j]
    if value is None or value < 0:
        return 0.0
    return float(value)


def effective_bets(weights: Sequence[float], rho: Sequence[Sequence[float | None]]) -> float:
    """Nombre de paris indépendants, arrondi à 2 décimales ; 0.0 sans poids positif."""
    total = sum(w for w in weights if w > 0)
    if total <= 0:
        return 0.0
    w = [max(weight, 0.0) / total for weight in weights]
    n = len(w)
    concentration = sum(w[i] * w[j] * _clean_rho(rho, i, j) for i in range(n) for j in range(n))
    return round(1 / concentration, 2)


def _linkage(rho: Sequence[Sequence[float | None]], left: list[int], right: list[int]) -> float:
    """Liaison moyenne entre deux groupes : moyenne des ρ (inconnu → 0) entre leurs membres."""
    pairs = [_clean_rho(rho, i, j) for i in left for j in right]
    return sum(pairs) / len(pairs)


def _mean_inner_rho(rho: Sequence[Sequence[float | None]], members: list[int]) -> float:
    pairs = [_clean_rho(rho, a, b) for pos, a in enumerate(members) for b in members[pos + 1 :]]
    return sum(pairs) / len(pairs)


def correlation_blocks(
    keys: Sequence[str],
    weights: Sequence[float],
    rho: Sequence[Sequence[float | None]],
    threshold: float = BLOCK_CORRELATION,
) -> list[Block]:
    """Regroupement agglomératif en liaison moyenne, arrêté dès que la meilleure liaison passe sous `threshold`.

    Seuls les blocs d'au moins deux membres sont rendus, triés par poids décroissant."""
    groups: list[list[int]] = [[i] for i in range(len(keys))]
    while len(groups) > 1:
        best: tuple[float, int, int] | None = None
        for a in range(len(groups)):
            for b in range(a + 1, len(groups)):
                link = _linkage(rho, groups[a], groups[b])
                if best is None or link > best[0]:
                    best = (link, a, b)
        if best is None or best[0] < threshold:
            break
        _, a, b = best
        groups[a] = sorted(groups[a] + groups[b])
        del groups[b]

    total = sum(w for w in weights if w > 0)
    blocks = [
        Block(
            keys=tuple(keys[i] for i in group),
            weight_pct=round(sum(max(weights[i], 0.0) for i in group) / total * 100, 2) if total > 0 else 0.0,
            mean_rho=round(_mean_inner_rho(rho, group), 2),
        )
        for group in groups
        if len(group) >= 2
    ]
    return sorted(blocks, key=lambda block: block.weight_pct, reverse=True)
