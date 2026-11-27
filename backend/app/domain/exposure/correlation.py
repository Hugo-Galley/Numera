"""Corrélation entre expositions : par les cours, sinon par la composition (spec sur-exposition § 3, calculs purs).

Pour chaque paire : Pearson des rendements hebdomadaires en EUR quand l'historique commun suffit (`prices`), sinon
similarité cosinus des vecteurs de composition (`composition`), sinon ρ inconnu (`unknown`, `None`)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.domain.etf_composition import EtfLine, is_equity
from app.domain.etf_normalize import UNKNOWN_LABEL
from app.domain.exposure.identity import Kind
from app.domain.exposure.stats import correlation, cosine
from app.domain.holdings import normalize_ticker

Source = Literal["prices", "composition", "unknown"]
FULL_WEIGHT = 100


@dataclass(frozen=True)
class Matrix:
    keys: tuple[str, ...]
    rho: tuple[tuple[float | None, ...], ...]  # diagonale à 1
    source: tuple[tuple[Source, ...], ...]


def pair_correlation(
    returns_a: Mapping[date, float] | None,
    returns_b: Mapping[date, float] | None,
    vector_a: Mapping[str, float] | None,
    vector_b: Mapping[str, float] | None,
) -> tuple[float | None, Source]:
    """ρ d'une paire et sa source : cours, sinon composition, sinon inconnu."""
    if returns_a and returns_b:
        rho = correlation(returns_a, returns_b)
        if rho is not None:
            return rho, "prices"
    if vector_a and vector_b:
        return cosine(vector_a, vector_b), "composition"
    return None, "unknown"


def correlation_matrix(
    keys: Sequence[str],
    returns: Mapping[str, Mapping[date, float]],
    vectors: Mapping[str, Mapping[str, float]],
) -> Matrix:
    """Matrice symétrique des ρ entre expositions (`keys`), avec la source de chaque paire."""
    n = len(keys)
    rho: list[list[float | None]] = [[1.0] * n for _ in range(n)]
    source: list[list[Source]] = [["unknown"] * n for _ in range(n)]
    for i, a in enumerate(keys):
        for j in range(i, n):
            b = keys[j]
            value, origin = pair_correlation(returns.get(a), returns.get(b), vectors.get(a), vectors.get(b))
            if i != j:
                rho[i][j] = rho[j][i] = value
            source[i][j] = source[j][i] = origin
    return Matrix(keys=tuple(keys), rho=tuple(map(tuple, rho)), source=tuple(map(tuple, source)))


def _known(label: str | None) -> bool:
    return bool(label) and label != UNKNOWN_LABEL


def _add(vector: dict[str, float], key: str, weight: float) -> None:
    vector[key] = vector.get(key, 0.0) + weight


def composition_vector(
    kind: Kind,
    lines: Sequence[EtfLine],
    isin: str | None,
    ticker: str,
    country: str | None,
    sector: str | None,
) -> dict[str, float]:
    """Vecteur creux de composition : sociétés (`isin:`), pays (`c:`), secteurs (`s:`), ou `crypto:`.

    Un fonds : ses lignes actions pondérées ; une action en direct : 100 % d'elle-même, de son pays et de son secteur
    (clés absentes si inconnus) ; une crypto : 100 % d'elle-même."""
    if kind == "crypto":
        return {f"crypto:{normalize_ticker(ticker)}": FULL_WEIGHT}
    if kind == "direct":
        vector: dict[str, float] = {f"isin:{(isin or ticker).strip().upper()}": FULL_WEIGHT}
        if country and _known(country):
            vector[f"c:{country}"] = FULL_WEIGHT
        if sector and _known(sector):
            vector[f"s:{sector}"] = FULL_WEIGHT
        return vector
    vector = {}
    for line in lines:
        if not is_equity(line) or line.weight <= 0:
            continue
        identifier = line.isin or line.ticker
        if identifier:
            _add(vector, f"isin:{identifier.strip().upper()}", line.weight)
        if line.country and _known(line.country):
            _add(vector, f"c:{line.country}", line.weight)
        if _known(line.sector):
            _add(vector, f"s:{line.sector}", line.weight)
    return vector
