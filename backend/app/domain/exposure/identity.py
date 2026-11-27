"""Identité : des positions valorisées (tous comptes) aux expositions (spec sur-exposition § 1).

Deux positions sont la même exposition si elles portent le même titre (ISIN ou ticker normalisé), le même profil ETF,
ou, entre fonds seulement, le même indice (`index_name`, référence physique d'un synthétique, ou `same_fund` fourni par
l'appelant : tracking error ou similarité de composition). Deux fonds dont les indices sont connus et différents ne
fusionnent jamais."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from app.domain.holdings import normalize_ticker

Kind = Literal["fund", "direct", "crypto"]


@dataclass(frozen=True)
class Holding:
    id: int
    account_id: int
    ticker: str
    isin: str | None
    name: str
    value_eur: float
    kind: Kind
    profile_id: int | None
    exposure_profile_id: int | None
    index_name: str | None


@dataclass(frozen=True)
class ExposureGroup:
    key: str  # "exp:<ticker normalisé du plus gros support>"
    name: str  # nom du plus gros support
    kind: Kind
    value_eur: float
    holdings: tuple[Holding, ...]  # par valeur décroissante


def _never(a: Holding, b: Holding) -> bool:
    return False


def _same_security(a: Holding, b: Holding) -> bool:
    if a.isin and b.isin and a.isin.strip().upper() == b.isin.strip().upper():
        return True
    return normalize_ticker(a.ticker) == normalize_ticker(b.ticker)


def _same_index(a: Holding, b: Holding) -> bool:
    if a.index_name and b.index_name and a.index_name.strip().casefold() == b.index_name.strip().casefold():
        return True
    if a.exposure_profile_id is not None and a.exposure_profile_id == b.profile_id:
        return True
    if b.exposure_profile_id is not None and b.exposure_profile_id == a.profile_id:
        return True
    return a.exposure_profile_id is not None and a.exposure_profile_id == b.exposure_profile_id


def _different_indices(a: Holding, b: Holding) -> bool:
    """Deux indices connus et différents (S&P 500 contre MSCI World) : jamais la même exposition."""
    return bool(a.index_name and b.index_name) and (
        (a.index_name or "").strip().casefold() != (b.index_name or "").strip().casefold()
    )


def _same_exposure(a: Holding, b: Holding, same_fund: Callable[[Holding, Holding], bool]) -> bool:
    if _same_security(a, b):
        return True
    if a.profile_id is not None and a.profile_id == b.profile_id:
        return True
    if a.kind != "fund" or b.kind != "fund":
        return False
    if _same_index(a, b):
        return True
    # La règle de repli (cours, composition) ne départage que si au moins un indice est inconnu
    return not _different_indices(a, b) and same_fund(a, b)


def _find(parent: list[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def group_exposures(
    holdings: Sequence[Holding],
    same_fund: Callable[[Holding, Holding], bool] = _never,
) -> list[ExposureGroup]:
    """Fusionne (union-find) les positions de valeur > 0 qui sont la même exposition, triées par valeur décroissante."""
    items = [h for h in holdings if h.value_eur > 0]
    parent = list(range(len(items)))
    for i, a in enumerate(items):
        for j in range(i + 1, len(items)):
            if _find(parent, i) != _find(parent, j) and _same_exposure(a, items[j], same_fund):
                parent[_find(parent, j)] = _find(parent, i)

    members: dict[int, list[Holding]] = {}
    for i, h in enumerate(items):
        members.setdefault(_find(parent, i), []).append(h)

    groups = []
    for group in members.values():
        ordered = tuple(sorted(group, key=lambda h: h.value_eur, reverse=True))
        main = ordered[0]
        groups.append(
            ExposureGroup(
                key=f"exp:{normalize_ticker(main.ticker)}",
                name=main.name,
                kind=main.kind,
                value_eur=sum(h.value_eur for h in ordered),
                holdings=ordered,
            )
        )
    return sorted(groups, key=lambda g: g.value_eur, reverse=True)
