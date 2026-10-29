"""Capital net investi d'un compte suivi par relevés : base (Point Zéro ou valeur en début de période) + versements − retraits."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.integrations.currency import convert_amount
from app.models.account import Account
from app.repositories.analytics import investments as repo

INTEREST_CATEGORIES = ["Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"]
FEE_KEYWORDS = ["achat", "frais", "commission", "tax"]


async def calculate_investment_flows(db: Session, account: Account, end_date: datetime, start_date: datetime | None = None,
                                     target_currency: str = "EUR") -> dict:
    baseline_val_raw, baseline_date = _baseline(db, account, end_date, start_date)
    baseline_val_target = 0.0
    if baseline_val_raw != 0:
        baseline_val_target = await convert_amount(
            baseline_val_raw, account.currency, target_currency, date=baseline_date.date() if baseline_date else None, db=db
        )
    verse, retire, last_flow_date = await _operation_flows(db, account, end_date, start_date, baseline_date, target_currency)
    # Les flux bancaires s'ajoutent un à un aux totaux (même ordre d'addition qu'un seul cumul)
    total_verse_target, total_retire_target = await _bank_flows(
        db, account, end_date, start_date, baseline_date, target_currency, verse, retire
    )
    return {
        "baseline_val_target": baseline_val_target,
        "baseline_date": baseline_date,
        "total_verse_target": total_verse_target,
        "total_retire_target": total_retire_target,
        "last_flow_date": last_flow_date,
        "net_invested_target": baseline_val_target + total_verse_target - total_retire_target
    }


def _baseline(db: Session, account: Account, end_date: datetime, start_date: datetime | None) -> tuple[float, datetime | None]:
    """Sur une période : valeur avant son début (relevé, sinon solde). Sur tout l'historique : dernier Point Zéro."""
    if start_date:
        last_snap = repo.last_snapshot_before(db, account.id, start_date)
        if last_snap:
            return float(last_snap.current_value), last_snap.date
        # Compte ouvert pendant la période : base nulle, Solde Initial et versements comptés comme flux
        last_tx = repo.last_transaction(db, account.id, before=start_date)
        if last_tx:
            return float(last_tx.running_balance), last_tx.date
        return 0.0, None
    zero_point = repo.latest_zero_point(db, account.id, until=end_date)
    if zero_point:
        return float(zero_point.current_value), zero_point.date
    return 0.0, None


async def _operation_flows(db: Session, account: Account, end_date: datetime, start_date: datetime | None,
                           baseline_date: datetime | None, target_currency: str) -> tuple[float, float, datetime | None]:
    """Versements et retraits des opérations d'investissement, et date du dernier de ces flux."""
    verse = retire = 0.0
    last_flow_date: datetime | None = None
    # Sur tout l'historique, seules les opérations postérieures au Point Zéro comptent
    for tx in repo.investment_operations(db, account.id, until=end_date, since=start_date, after=baseline_date):
        amount_target = await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
        if tx.type == "versement":
            verse += amount_target
            last_flow_date = max(last_flow_date, tx.date) if last_flow_date else tx.date
        elif tx.type == "retrait":
            retire += amount_target
            last_flow_date = max(last_flow_date, tx.date) if last_flow_date else tx.date
    return verse, retire, last_flow_date


async def _bank_flows(db: Session, account: Account, end_date: datetime, start_date: datetime | None,
                      baseline_date: datetime | None, target_currency: str, verse: float,
                      retire: float) -> tuple[float, float]:
    """Ajoute à `verse`/`retire` les flux portés par les transactions bancaires du compte (hors intérêts, dividendes et frais)."""
    # Un compte qui a des opérations d'investissement n'est alimenté par ses transactions bancaires que via
    # ses virements (un virement vers une assurance-vie crée une Entree, pas un versement)
    rtxs = repo.account_transactions(
        db, account.id, until=end_date, since=start_date, after=baseline_date,
        transfer_legs_only=repo.has_investment_operations(db, account.id),
    )
    for tx in rtxs:
        merchant_lower = (tx.merchant or "").lower()
        if tx.type == "Solde Initial" or tx.type == "Entree":
            # Intérêts et dividendes sont des gains, pas du capital
            if tx.category and tx.category.name in INTEREST_CATEGORIES:
                continue
            if "dividende" in merchant_lower:
                continue
            amount_target = await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
            # « Vente » sur un compte titres : argent rendu par le marché, compté en retrait
            if "vente" in merchant_lower:
                retire += amount_target
            else:
                verse += amount_target
        elif tx.type == "Sortie":
            # Frais et taxes font partie de la performance, pas des flux de capital
            if any(k in merchant_lower for k in FEE_KEYWORDS):
                continue
            retire += await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
    return verse, retire
