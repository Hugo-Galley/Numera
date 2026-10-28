"""Rapprochement d'un compte avec le solde affiché par la banque.

Lecture seule : compare le solde de la banque à une date au `running_balance` de Numera ce
jour-là, puis cherche les transactions qui expliqueraient l'écart (doublon, montant égal à
l'écart, sens inversé). Rien n'est corrigé automatiquement ; un écart nul marque le compte
vérifié (`last_verified_at`) côté endpoint.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.repositories import reconciliation as repo

# Écart toléré (arrondis) et fenêtre de recherche des causes avant la date du relevé
TOLERANCE = 0.01
WINDOW_DAYS = 60
# Deux lignes identiques à moins de 3 jours d'écart = doublon probable (import en double, saisie + import)
DUPLICATE_MAX_DAYS = 3


@dataclass
class Hint:
    kind: str  # duplicate | extra_or_missing | wrong_sign | missing
    message: str
    transactions: list[Transaction] = field(default_factory=list)


@dataclass
class Reconciliation:
    numera_balance: float
    gap: float  # banque − Numera : > 0 → Numera sous-estime le solde
    matches: bool
    hints: list[Hint]


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE


def balance_at(db: Session, account_id: int, day: date) -> float:
    """Solde de Numera à la fin du jour `day` (dernier `running_balance` connu, 0 sans transaction)."""
    end = datetime.combine(day + timedelta(days=1), datetime.min.time())
    last = repo.last_before(db, account_id, end)
    return round(float(last.running_balance), 2) if last else 0.0


def _signed_effect(tx: Transaction) -> float:
    """Effet de la ligne sur le solde (`Solde Initial` exclu : il remplace le solde)."""
    if tx.type == "Sortie":
        return -float(tx.amount)
    if tx.type in ("Entree", "Interets"):
        return float(tx.amount)
    return 0.0


def _fmt(amount: float, currency: str) -> str:
    return f"{abs(amount):,.2f} {currency}".replace(",", " ").replace(".", ",")


def _is_duplicate(tx: Transaction, other: Transaction) -> bool:
    return (
        other.type == tx.type
        and _close(float(other.amount), float(tx.amount))
        and (other.merchant or "").strip().lower() == (tx.merchant or "").strip().lower()
        and abs((tx.date - other.date).days) <= DUPLICATE_MAX_DAYS
    )


def _duplicate_hints(window: list[Transaction], gap: float, currency: str, seen: set[int]) -> list[Hint]:
    """Doublons probables : même sens, montant et libellé à quelques jours d'écart. Retirer le doublon
    change le solde de -effet ; il n'explique l'écart que si le sens correspond."""
    hints: list[Hint] = []
    for i, tx in enumerate(window):
        if tx.id in seen or tx.is_duplicate_ignored:
            continue
        for other in window[i + 1:]:
            if other.id in seen or other.is_duplicate_ignored:
                continue
            if _is_duplicate(tx, other):
                effect = _signed_effect(tx)
                explains = _close(-effect, gap)
                if explains or (effect != 0 and (-effect) * gap > 0):
                    seen.update({tx.id, other.id})
                    hints.append(Hint(
                        kind="duplicate",
                        message=(
                            f"Doublon probable : « {tx.merchant} » ({_fmt(effect, currency)}) apparaît deux fois"
                            + (" et explique exactement l'écart." if explains else ".")
                        ),
                        transactions=[tx, other],
                    ))
                break
    return hints


def _single_line_hints(window: list[Transaction], gap: float, currency: str, seen: set[int]) -> list[Hint]:
    """Une ligne dont le montant égale l'écart (en trop, ou pas encore passée à la banque), puis une ligne
    saisie dans le mauvais sens (elle décale le solde de deux fois son montant)."""
    hints: list[Hint] = []
    for tx in window:
        effect = _signed_effect(tx)
        if tx.id not in seen and effect and _close(-effect, gap):
            seen.add(tx.id)
            hints.append(Hint(
                kind="extra_or_missing",
                message=(
                    f"« {tx.merchant} » ({_fmt(effect, currency)}) correspond exactement à l'écart : "
                    "ligne en trop, ou pas encore passée à la banque à cette date ?"
                ),
                transactions=[tx],
            ))
    for tx in window:
        effect = _signed_effect(tx)
        if tx.id not in seen and effect and _close(-2 * effect, gap):
            seen.add(tx.id)
            hints.append(Hint(
                kind="wrong_sign",
                message=(
                    f"« {tx.merchant} » ({_fmt(effect, currency)}) est peut-être enregistrée dans le mauvais sens "
                    f"({tx.type}) : l'inverser comblerait l'écart."
                ),
                transactions=[tx],
            ))
    return hints


def _missing_hint(gap: float, currency: str, day: date) -> Hint:
    """Repli : sans piste, l'écart est probablement une transaction absente de Numera."""
    kind_label = "une entrée" if gap > 0 else "une dépense"
    return Hint(
        kind="missing",
        message=(
            f"Aucune ligne n'explique l'écart : il manque probablement {kind_label} de "
            f"{_fmt(gap, currency)} (ou plusieurs) avant le {day.strftime('%d/%m/%Y')}."
        ),
    )


def reconcile(db: Session, account_id: int, day: date, bank_balance: float, currency: str) -> Reconciliation:
    numera = balance_at(db, account_id, day)
    gap = round(bank_balance - numera, 2)
    if _close(gap, 0):
        return Reconciliation(numera_balance=numera, gap=0.0, matches=True, hints=[])

    end = datetime.combine(day + timedelta(days=1), datetime.min.time())
    window = repo.window(db, account_id, end - timedelta(days=WINDOW_DAYS + 1), end)
    seen: set[int] = set()
    hints = _duplicate_hints(window, gap, currency, seen)
    hints += _single_line_hints(window, gap, currency, seen)
    return Reconciliation(numera_balance=numera, gap=gap, matches=False, hints=hints or [_missing_hint(gap, currency, day)])
