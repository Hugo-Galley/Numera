"""Virements internes : liaison, déliaison, rapprochement par règles et création de contrepartie.

Un virement est un couple 1 pour 1 : une `Sortie` et une `Entree` (ou un `versement` d'investissement)
sur deux comptes différents. Un lien ne modifie aucun montant.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core import currency as currency_module
from app.core.finance import month_label_from_date
from app.core.logging import get_logger
from app.core.time import utcnow_naive
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction
from app.models.transfer_rule import TransferRule

logger = get_logger(__name__)

# Origines pour lesquelles un « délier » doit empêcher la liaison automatique de recommencer
AUTO_ORIGINS = ("rule", "recurring")
EVENT_MONTHS = 3  # fenêtre des rapprochements déclenchés par un événement (import, saisie…)

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


def _clear(leg: Leg, ignore: bool) -> None:
    leg.linked_transaction_id = None
    if isinstance(leg, Transaction):
        leg.linked_investment_transaction_id = None
    leg.is_transfer = False
    leg.link_origin = None
    leg.transfer_rule_id = None
    if ignore:
        leg.is_transfer_ignored = True


def _partners(db: Session, tx: Transaction) -> list[Leg]:
    partners: list[Leg] = []
    if tx.linked_transaction_id:
        other = db.get(Transaction, tx.linked_transaction_id)
        if other:
            partners.append(other)
    if tx.linked_investment_transaction_id:
        other_inv = db.get(InvestmentTransaction, tx.linked_investment_transaction_id)
        if other_inv:
            partners.append(other_inv)
    return partners


def _detach(db: Session, tx: Transaction, *, mark_ignored: bool) -> None:
    ignore = mark_ignored and tx.link_origin in AUTO_ORIGINS
    for partner in _partners(db, tx):
        _clear(partner, ignore)
    _clear(tx, ignore)


def unlink_pair(db: Session, tx: Transaction) -> None:
    """Délie `tx` et son partenaire. Un lien automatique délié est marqué « ignoré » des deux côtés."""
    _detach(db, tx, mark_ignored=True)


def link_pair(db: Session, sortie: Transaction, other: Leg, kind: str, origin: str, rule_id: int | None = None) -> None:
    """Relie `sortie` à `other` (Transaction si kind="regular", InvestmentTransaction si "investment")."""
    if kind not in ("regular", "investment"):
        raise ValueError("kind must be 'regular' or 'investment'")
    if kind == "regular" and other.id == sortie.id:
        raise ValueError("A transaction cannot be linked to itself")

    # Libère les anciens partenaires pour ne laisser aucun lien orphelin
    _detach(db, sortie, mark_ignored=False)
    if kind == "regular":
        _detach(db, other, mark_ignored=False)
        sortie.linked_transaction_id = other.id
    else:
        if other.linked_transaction_id and other.linked_transaction_id != sortie.id:
            previous = db.get(Transaction, other.linked_transaction_id)
            if previous:
                _clear(previous, False)
        sortie.linked_investment_transaction_id = other.id
    other.linked_transaction_id = sortie.id

    for leg in (sortie, other):
        leg.is_transfer = True
        leg.link_origin = origin
        leg.transfer_rule_id = rule_id


def _matches_pattern(tx: Transaction, pattern: str | None) -> bool:
    if not pattern:
        return True
    needle = pattern.lower()
    return needle in (tx.merchant or "").lower() or needle in (tx.note or "").lower()


async def find_pairs(
    db: Session,
    *,
    source_account_id: int | None = None,
    dest_account_id: int | None = None,
    pattern: str | None = None,
    amount: float | None = None,
    amount_tolerance_pct: float = 1.0,
    day_tolerance: int = 3,
    months: int | None = None,
    rule_id: int | None = None,
) -> list[Pair]:
    """Appariement 1 pour 1 des sorties et des entrées non liées.

    Les arêtes (sortie, entrée) sont triées par écart de date puis de montant et affectées au plus
    proche d'abord : une entrée ne sert jamais deux sorties. Quand plusieurs arêtes ont exactement
    le même écart, elles sont toutes renvoyées avec `ambiguous=True` (à confirmer à la main).
    """
    accounts = {a.id: a for a in db.query(Account).all()}
    rates = await currency_module.get_exchange_rates("EUR")

    def to_eur(value: float, account_id: int) -> float:
        currency = accounts[account_id].currency if account_id in accounts else "EUR"
        return value / rates.get(currency, 1.0)

    since = None
    if months:
        since = utcnow_naive() - timedelta(days=30 * months)

    sorties_q = db.query(Transaction).filter(
        Transaction.type == "Sortie",
        Transaction.is_transfer.is_(False),
        Transaction.is_transfer_ignored.is_(False),
        Transaction.linked_transaction_id.is_(None),
        Transaction.linked_investment_transaction_id.is_(None),
    )
    if source_account_id is not None:
        sorties_q = sorties_q.filter(Transaction.account_id == source_account_id)
    if since:
        sorties_q = sorties_q.filter(Transaction.date >= since)
    sorties = [s for s in sorties_q.all() if _matches_pattern(s, pattern)]
    if amount is not None:
        sorties = [s for s in sorties if abs(s.amount - amount) / max(abs(amount), 1.0) * 100.0 <= amount_tolerance_pct]

    dest = accounts.get(dest_account_id) if dest_account_id is not None else None
    want_regular = dest is None or dest.type != "investissement"
    want_investment = dest is None or dest.type == "investissement"
    date_floor = since - timedelta(days=day_tolerance) if since else None

    buckets: dict[int, list[tuple[str, Leg]]] = defaultdict(list)
    if want_regular:
        q = db.query(Transaction).filter(
            Transaction.type == "Entree",
            Transaction.is_transfer.is_(False),
            Transaction.is_transfer_ignored.is_(False),
            Transaction.linked_transaction_id.is_(None),
        )
        if dest_account_id is not None:
            q = q.filter(Transaction.account_id == dest_account_id)
        if date_floor:
            q = q.filter(Transaction.date >= date_floor)
        for e in q.all():
            buckets[e.date.toordinal()].append(("regular", e))
    if want_investment:
        q = db.query(InvestmentTransaction).filter(
            InvestmentTransaction.type == "versement",
            InvestmentTransaction.is_transfer.is_(False),
            InvestmentTransaction.is_transfer_ignored.is_(False),
            InvestmentTransaction.linked_transaction_id.is_(None),
        )
        if dest_account_id is not None:
            q = q.filter(InvestmentTransaction.account_id == dest_account_id)
        if date_floor:
            q = q.filter(InvestmentTransaction.date >= date_floor)
        for e in q.all():
            buckets[e.date.toordinal()].append(("investment", e))

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


async def apply_rules(
    db: Session, *, rule_ids: list[int] | None = None, dry_run: bool = False, months: int | None = None
) -> list[Pair]:
    """Lie automatiquement les couples sans ambiguïté trouvés par les règles actives."""
    q = db.query(TransferRule).filter(TransferRule.is_active.is_(True))
    if rule_ids:
        q = q.filter(TransferRule.id.in_(rule_ids))
    linked: list[Pair] = []
    seen_sorties: set[int] = set()
    for rule in q.order_by(TransferRule.id).all():
        pairs = await find_pairs(
            db,
            source_account_id=rule.source_account_id,
            dest_account_id=rule.dest_account_id,
            pattern=rule.pattern,
            amount=rule.amount,
            amount_tolerance_pct=rule.amount_tolerance_pct,
            day_tolerance=rule.day_tolerance,
            months=months,
            rule_id=rule.id,
        )
        for p in pairs:
            if p.ambiguous or p.sortie.id in seen_sorties:
                continue
            seen_sorties.add(p.sortie.id)
            if not dry_run:
                link_pair(db, p.sortie, p.entree, p.kind, "rule", rule.id)
            linked.append(p)
        if not dry_run:
            db.flush()
    if linked and not dry_run:
        db.commit()
    return linked


async def auto_link_transfers(db: Session) -> int:
    """Rapprochement déclenché par un événement : ne doit jamais faire échouer l'appelant."""
    try:
        return len(await apply_rules(db, months=EVENT_MONTHS))
    except Exception:
        logger.exception("Automatic transfer matching failed")
        db.rollback()
        return 0


async def create_counterpart(
    db: Session,
    sortie: Transaction,
    dest: Account,
    *,
    date: datetime | None = None,
    amount: float | None = None,
    origin: str = "manual",
    recurring_transaction_id: int | None = None,
    trade: dict | None = None,
) -> tuple[Leg, str]:
    """Crée l'entrée (ou le versement) manquante sur `dest` et la relie à `sortie`.

    `amount` est exprimé dans la devise de `dest` ; par défaut, le montant de la sortie converti.
    L'appelant recalcule les soldes de `dest` (`recalculate_running_balances`) pour un compte courant.
    `trade` (compte investissement) : titre, quantité et prix du versement, qui est alors un dépôt
    et un achat de parts en une seule opération (l'appelant relance `rebuild_holdings`).
    """
    src = db.get(Account, sortie.account_id)
    when = date or sortie.date
    if amount is None:
        amount = sortie.amount
        if src.currency != dest.currency:
            amount = await currency_module.convert_amount(sortie.amount, src.currency, dest.currency, date=when.date(), db=db)

    leg: Leg
    if dest.type == "investissement":
        kind = "investment"
        leg = InvestmentTransaction(
            account_id=dest.id, date=when, type="versement", amount=amount, original_amount=amount,
            currency=dest.currency, note=f"Virement depuis {src.name}",
            recurring_transaction_id=recurring_transaction_id,
            **(trade or {}),
        )
    else:
        kind = "regular"
        leg = Transaction(
            account_id=dest.id, date=when, month_label=month_label_from_date(when), type="Entree",
            merchant=f"Virement depuis {src.name}", amount=amount, original_amount=amount,
            currency=dest.currency, running_balance=0.0,
            is_recurring=recurring_transaction_id is not None,
            recurring_transaction_id=recurring_transaction_id,
        )
    db.add(leg)
    db.flush()
    link_pair(db, sortie, leg, kind, origin)
    return leg, kind


async def candidates_for(
    db: Session,
    tx: Transaction,
    *,
    days: int = 15,
    amount_tolerance_pct: float = 5.0,
    account_id: int | None = None,
    limit: int = 30,
) -> list[dict]:
    """Candidates pour relier `tx` à la main, classées par écart de date puis de montant.

    Pour une `Sortie`, on cherche des entrées (ou versements) ; pour une `Entree`, des sorties.
    Chaque candidate porte `sortie_id` / `other_id` / `type`, directement utilisables avec
    `POST /transactions/{sortie_id}/link/{other_id}?type=`.
    """
    accounts = {a.id: a for a in db.query(Account).all()}
    rates = await currency_module.get_exchange_rates("EUR")

    def to_eur(value: float, acc_id: int) -> float:
        currency = accounts[acc_id].currency if acc_id in accounts else "EUR"
        return value / rates.get(currency, 1.0)

    reference = to_eur(tx.amount, tx.account_id)
    low = tx.date - timedelta(days=days)
    high = tx.date + timedelta(days=days, hours=23, minutes=59)

    rows: list[tuple[str, Leg]] = []
    if tx.type == "Sortie":
        wanted = [(Transaction, "Entree", "regular"), (InvestmentTransaction, "versement", "investment")]
    elif tx.type == "Entree":
        wanted = [(Transaction, "Sortie", "regular")]
    else:
        return []
    for model, type_, kind in wanted:
        q = db.query(model).filter(
            model.type == type_, model.is_transfer.is_(False),
            model.account_id != tx.account_id, model.date >= low, model.date <= high,
        )
        if account_id is not None:
            q = q.filter(model.account_id == account_id)
        rows.extend((kind, leg) for leg in q.all())

    out = []
    for kind, leg in rows:
        gap = abs(to_eur(leg.amount, leg.account_id) - reference) / max(reference, 1.0) * 100.0
        if gap > amount_tolerance_pct:
            continue
        sortie_id, other_id = (tx.id, leg.id) if tx.type == "Sortie" else (leg.id, tx.id)
        out.append({
            "sortie_id": sortie_id,
            "other_id": other_id,
            "type": kind,
            "account_id": leg.account_id,
            "date": leg.date,
            "amount": leg.amount,
            "currency": leg.currency,
            "label": getattr(leg, "merchant", None) or leg.note,
            "day_gap": abs((leg.date.date() - tx.date.date()).days),
            "amount_gap_pct": round(gap, 4),
        })
    out.sort(key=lambda c: (c["day_gap"], c["amount_gap_pct"], c["other_id"]))
    return out[:limit]
