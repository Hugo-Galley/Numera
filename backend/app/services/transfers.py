"""Virements internes : liaison, déliaison, rapprochement par règles et création de contrepartie.

Un virement est un couple 1 pour 1 : une `Sortie` et une `Entree` (ou un `versement` d'investissement)
sur deux comptes différents. Un lien ne modifie aucun montant.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core import currency as currency_module
from app.domain.finance import month_label_from_date
from app.core.logging import get_logger
from app.core.time import utcnow_naive
from app.domain.transfers import Leg, Pair, match_pairs, matches_pattern
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction
from app.repositories import transfers as repo

logger = get_logger(__name__)

# Origines pour lesquelles un « délier » doit empêcher la liaison automatique de recommencer
AUTO_ORIGINS = ("rule", "recurring")
EVENT_MONTHS = 3  # fenêtre des rapprochements déclenchés par un événement (import, saisie…)

async def _eur_converter(accounts: dict[int, Account]):
    """Convertisseur montant -> EUR selon la devise du compte (taux courants)."""
    rates = await currency_module.get_exchange_rates("EUR")

    def to_eur(value: float, account_id: int) -> float:
        currency = accounts[account_id].currency if account_id in accounts else "EUR"
        return value / rates.get(currency, 1.0)

    return to_eur


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


def release_partner(db: Session, tx: Transaction) -> None:
    """Délie `tx` et son partenaire sans marquer « ignoré » (avant la suppression de `tx`)."""
    _detach(db, tx, mark_ignored=False)


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

    sortie.splits = []  # un virement interne n'est pas une dépense : son découpage n'a plus de sens
    for leg in (sortie, other):
        leg.is_transfer = True
        leg.link_origin = origin
        leg.transfer_rule_id = rule_id


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
    accounts = repo.accounts_by_id(db)
    to_eur = await _eur_converter(accounts)
    since = utcnow_naive() - timedelta(days=30 * months) if months else None

    sorties = [s for s in repo.unlinked_sorties(db, source_account_id, since) if matches_pattern(s, pattern)]
    if amount is not None:
        sorties = [s for s in sorties if abs(s.amount - amount) / max(abs(amount), 1.0) * 100.0 <= amount_tolerance_pct]

    dest = accounts.get(dest_account_id) if dest_account_id is not None else None
    date_floor = since - timedelta(days=day_tolerance) if since else None
    entrees: list[tuple[str, Leg]] = []
    if dest is None or dest.type != "investissement":
        entrees += [("regular", e) for e in repo.unlinked_entrees(db, dest_account_id, date_floor)]
    if dest is None or dest.type == "investissement":
        entrees += [("investment", e) for e in repo.unlinked_versements(db, dest_account_id, date_floor)]

    return match_pairs(
        sorties, entrees, to_eur,
        day_tolerance=day_tolerance, amount_tolerance_pct=amount_tolerance_pct, rule_id=rule_id,
    )


async def apply_rules(
    db: Session, *, rule_ids: list[int] | None = None, dry_run: bool = False, months: int | None = None
) -> list[Pair]:
    """Lie automatiquement les couples sans ambiguïté trouvés par les règles actives."""
    linked: list[Pair] = []
    seen_sorties: set[int] = set()
    for rule in repo.active_rules(db, rule_ids):
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
    to_eur = await _eur_converter(repo.accounts_by_id(db))
    reference = to_eur(tx.amount, tx.account_id)
    if repo.is_locked(db, tx.id):
        return []
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
        rows.extend((kind, leg) for leg in repo.legs_near(db, model, type_, tx.account_id, low, high, account_id))

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
