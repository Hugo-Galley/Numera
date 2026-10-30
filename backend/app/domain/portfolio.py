"""Règles pures de la valorisation d'un compte titres : flux externes, échantillonnage de la courbe, points.

Source de vérité d'un compte titres (PEA, CTO, crypto) : valeur = Σ quantité × cours + espèces, où
les espèces cumulent les flux d'opérations (`versement` +, `retrait` −, `achat` −, `vente` +, `frais` −,
`dividende` +) à partir de l'inventaire Point Zéro. Un versement/retrait portant un titre et une quantité
(ancien format « un seul mouvement ») est à la fois un flux externe et une opération : l'effet sur les
espèces s'annule. Les snapshots (`balance_snapshots`) ne servent plus qu'au rapprochement avec le relevé
du courtier.
"""
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime, timedelta

from app.domain.holdings import Replay
from app.models.account import Account
from app.models.transaction import Transaction

RECONCILIATION_THRESHOLD_PCT = 2.0
SNAPSHOT_MATCH_DAYS = 7

INTEREST_CATEGORIES = {"Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"}
FEE_KEYWORDS = ("achat", "frais", "commission", "tax")

# Versements antérieurs à l'inventaire : au-delà de ce multiple de la valeur d'ouverture, la performance est douteuse
PRE_INVENTORY_RATIO = 2.0
# En dessous de cette durée, le rendement annualisé (XIRR) n'est pas calculé
MIN_XIRR_DAYS = 30


@dataclass
class CashEvent:
    date: datetime
    cash: float  # variation des espèces (devise du compte)
    external: float = 0.0  # flux externe (versement + / retrait −), devise du compte


def classify_regular_flow(tx: Transaction) -> float:
    """Flux externe (signe) d'une transaction bancaire classique sur un compte titres, par mots-clés."""
    merchant = (tx.merchant or "").lower()
    if tx.type in ("Solde Initial", "Entree"):
        if tx.category and tx.category.name in INTEREST_CATEGORIES:
            return 0.0
        if "dividende" in merchant:
            return 0.0
        return -tx.amount if "vente" in merchant else tx.amount
    if tx.type == "Sortie":
        return 0.0 if any(k in merchant for k in FEE_KEYWORDS) else -tx.amount
    return 0.0


def sample_days(start: date_type, end: date_type, extra: set[date_type]) -> list[date_type]:
    """Jours de la courbe : bornes, jours imposés (flux, relevés) et un pas d'au moins 7 jours (≈ 300 points max)."""
    span = max((end - start).days, 1)
    step = max(7, -(-span // 300))
    days = {start, end} | {d for d in extra if start <= d <= end}
    day = start
    while day < end:
        days.add(day)
        day += timedelta(days=step)
    return sorted(days)


def uses_positions(account: Account, replay: Replay) -> bool:
    """Un compte titres ou une assurance-vie est valorisé par ses positions si son mode le demande et qu'il en a (ou a eu)."""
    return account.type in ("investissement", "assurance_vie") and account.valuation_mode == "positions" and bool(replay.positions or replay.baseline or replay.realized)


def history_point(day: str, value: float, invested: float) -> dict:
    """Point de la courbe : valeur, capital investi, gain et performance à date."""
    return {
        "date": day,
        "value": round(value, 2),
        "net_invested": round(invested, 2),
        "gain": round(value - invested, 2),
        "performance_pct": round((value - invested) / invested * 100.0, 2) if invested > 0 else None,
    }


def reconciliation_line(snapshot_date: datetime, snapshot_value: float, computed: float) -> dict:
    """Écart entre la valeur calculée et le relevé du courtier ; signalé au-delà du seuil."""
    gap = computed - snapshot_value
    gap_pct = gap / snapshot_value * 100.0 if snapshot_value else None
    return {
        "date": snapshot_date.isoformat(),
        "snapshot_value": round(snapshot_value, 2),
        "computed_value": round(computed, 2),
        "gap": round(gap, 2),
        "gap_pct": round(gap_pct, 2) if gap_pct is not None else None,
        "flagged": gap_pct is not None and abs(gap_pct) > RECONCILIATION_THRESHOLD_PCT,
    }
