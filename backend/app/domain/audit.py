"""Libellés du Centre d'Actions (calcul pur)."""
import re
import unicodedata

_MONTH_NAMES = ("janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre")
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def merchant_key(label: str) -> str:
    """Clé de rapprochement d'un libellé : sans accents, casse, chiffres ni ponctuation."""
    text = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z]+", " ", text).split())


def month_name(label: str) -> str:
    """« 2026-10 » → « octobre 2026 » (FRENCH_MONTHS, sans accents, sert aux libellés stockés)."""
    year, month = label.split("-")
    return f"{_MONTH_NAMES[int(month) - 1]} {year}"


def merchant_variants(rows: list[tuple[str, int]]) -> list[list[tuple[str, int]]]:
    """Libellés d'un même marchand (même clé), au moins deux, du groupe le plus fréquent au moins fréquent."""
    variants: dict[str, list[tuple[str, int]]] = {}
    for merchant, count in rows:
        key = merchant_key(merchant)
        if key:
            variants.setdefault(key, []).append((merchant, count))
    return sorted(
        (sorted(labels, key=lambda lc: -lc[1]) for labels in variants.values() if len(labels) >= 2),
        key=lambda labels: -sum(c for _, c in labels),
    )
