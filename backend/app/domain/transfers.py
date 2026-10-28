"""Appariement des virements internes : calcul pur sur des sorties et des entrées déjà chargées."""
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction

Leg = Transaction | InvestmentTransaction


@dataclass
class Pair:
    sortie: Transaction
    entree: Leg
    kind: str  # "regular" | "investment"
    day_gap: int
    amount_gap_pct: float
    ambiguous: bool = False
    rule_id: int | None = None

    @property
    def key(self) -> tuple[int, float]:
        return (self.day_gap, self.amount_gap_pct)

    @property
    def entree_key(self) -> tuple[str, int]:
        return (self.kind, self.entree.id)


def matches_pattern(tx: Transaction, pattern: str | None) -> bool:
    if not pattern:
        return True
    needle = pattern.lower()
    return needle in (tx.merchant or "").lower() or needle in (tx.note or "").lower()


def _edges(
    sorties: list[Transaction],
    entrees: list[tuple[str, Leg]],
    to_eur: Callable[[float, int], float],
    day_tolerance: int,
    amount_tolerance_pct: float,
    rule_id: int | None,
) -> list[Pair]:
    """Toutes les arêtes (sortie, entrée) compatibles, triées par écart de date puis de montant."""
    buckets: dict[int, list[tuple[str, Leg]]] = defaultdict(list)
    for kind, entree in entrees:
        buckets[entree.date.toordinal()].append((kind, entree))
    edges: list[Pair] = []
    for s in sorties:
        s_eur = to_eur(s.amount, s.account_id)
        base = s.date.toordinal()
        for delta in range(-day_tolerance, day_tolerance + 1):
            for kind, e in buckets.get(base + delta, []):
                if e.account_id == s.account_id:
                    continue
                gap = abs(to_eur(e.amount, e.account_id) - s_eur) / max(s_eur, 1.0) * 100.0
                if gap <= amount_tolerance_pct:
                    edges.append(Pair(s, e, kind, abs(delta), gap, rule_id=rule_id))
    edges.sort(key=lambda p: (p.day_gap, p.amount_gap_pct, p.sortie.id, p.entree.id))
    return edges


def match_pairs(
    sorties: list[Transaction],
    entrees: list[tuple[str, Leg]],
    to_eur: Callable[[float, int], float],
    *,
    day_tolerance: int,
    amount_tolerance_pct: float,
    rule_id: int | None = None,
) -> list[Pair]:
    """Appariement 1 pour 1 : arêtes affectées au plus proche d'abord, une entrée ne sert jamais deux
    sorties. Plusieurs arêtes au même écart exact sont toutes renvoyées avec `ambiguous=True`."""
    edges = _edges(sorties, entrees, to_eur, day_tolerance, amount_tolerance_pct, rule_id)
    by_sortie: dict[int, list[Pair]] = defaultdict(list)
    by_entree: dict[tuple[str, int], list[Pair]] = defaultdict(list)
    for p in edges:
        by_sortie[p.sortie.id].append(p)
        by_entree[p.entree_key].append(p)

    used_s: set[int] = set()
    used_e: set[tuple[str, int]] = set()
    result: list[Pair] = []
    for p in edges:
        if p.sortie.id in used_s or p.entree_key in used_e:
            continue
        rivals = [
            q for q in by_sortie[p.sortie.id] + by_entree[p.entree_key]
            if q is not p and q.key == p.key and q.sortie.id not in used_s and q.entree_key not in used_e
        ]
        group = [p, *rivals]
        for q in group:
            q.ambiguous = bool(rivals)
            used_s.add(q.sortie.id)
            used_e.add(q.entree_key)
            result.append(q)
    return result
