"""Génération des opérations récurrentes (tâche de fond horaire, déclenchement manuel).

Les récurrences gérées par la configuration salaire sont exclues : `services/salary_generation.py`
s'en charge seul (une double génération créait des centaines de salaires en double).
"""
import calendar
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core import market_data
from app.core.currency import CurrencyConversionError, convert_amount
from app.core.holdings import rebuild_holdings
from app.core.logging import get_logger
from app.domain.finance import get_recurring_occurrences, month_label_from_date
from app.domain.recurring import investment_leg_type
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.repositories import recurring as repo
from app.services.balances import recalculate_running_balances
from app.services.transfers import auto_link_transfers, create_counterpart

logger = get_logger(__name__)


async def _market_price(db: Session, ticker: str, day: date) -> tuple[float, str | None] | None:
    """Cours d'un titre pour l'échéance `day` : clôture historique du jour (échéance passée, y compris
    rattrapée après coup), sinon cotation en direct. None si aucun cours exploitable."""
    try:
        if day < date.today():
            hist = await market_data.get_price_on(db, ticker, day)
            if hist and hist["price"] and float(hist["price"]) > 0:
                return round(float(hist["price"]), 4), hist.get("currency")
        quotes = await market_data.get_market_quotes([ticker], db=db)
        q_data = quotes.get(ticker, {})
        if q_data.get("price") and float(q_data["price"]) > 0:
            return round(float(q_data["price"]), 4), q_data.get("currency")
    except Exception as e:
        logger.warning(f"Could not fetch a price for recurring buy of {ticker} on {day}: {e}")
    return None


async def _size_trade(
    db: Session, rd: RecurringTransaction, account_currency: str, amount: float, currency: str, occ: datetime
) -> tuple[float | None, float | None, str | None, float | None]:
    """Quantité, prix unitaire, devise du prix et montant réellement investi d'un achat récurrent de `amount`.

    Quantité et prix fixés dans la règle : repris tels quels. Sinon le prix vient du cours de clôture
    à la date de l'échéance (devise de cotation) et la quantité = montant ÷ prix. Avec `whole_shares`,
    la quantité est arrondie à l'entier inférieur : le montant investi (4e valeur, devise du compte)
    devient parts × cours, le reliquat reste en espèces chez le courtier (si le montant ne couvre pas une
    part entière, la quantité reste fractionnaire). Ce montant vaut None quand
    la règle n'impose pas de parts entières (ou si la taille de l'achat est inconnue).
    """
    unit_price = rd.unit_price
    quantity = rd.quantity
    price_currency = currency if unit_price else None  # prix fixé dans la règle : devise de la règle
    invested: float | None = None

    if rd.ticker and (not quantity or quantity <= 0 or not unit_price):
        market = await _market_price(db, rd.ticker.upper().strip(), occ.date())
        if market:
            unit_price, quoted_currency = market
            price_currency = quoted_currency or account_currency

    if (not quantity or quantity <= 0) and unit_price and unit_price > 0:
        try:
            price_in_account = await convert_amount(
                unit_price, price_currency or account_currency, account_currency, date=occ.date(), db=db
            )
            whole = math.floor(amount / price_in_account + 1e-9)
            if rd.whole_shares and whole >= 1:
                quantity = float(whole)
                invested = round(quantity * price_in_account, 2)
            else:
                # Montant inférieur au prix d'une part : on garde la quantité fractionnaire plutôt qu'un achat nul
                quantity = round(amount / price_in_account, 6)
        except CurrencyConversionError as exc:
            logger.warning(f"Recurring tx {rd.id}: cannot size the trade ({exc})")
    elif quantity and (not unit_price or unit_price <= 0) and amount > 0:
        unit_price = round(amount / quantity, 4)
        price_currency = account_currency
    return quantity, unit_price, price_currency, invested


def transfer_credit_date(debit: datetime, credit_day: int | None) -> datetime:
    """Date d'arrivée d'un virement récurrent débité le `debit` : le premier `credit_day` du mois
    (borné à la fin du mois) à partir du jour du débit. Sans jour d'arrivée, le jour du débit."""
    if not credit_day:
        return debit
    year, month = debit.year, debit.month
    while True:
        candidate = debit.replace(year=year, month=month, day=min(credit_day, calendar.monthrange(year, month)[1]))
        if candidate.date() >= debit.date():
            return candidate
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


async def _transfer_credit(
    db: Session, rd: RecurringTransaction, account: Account, dest: Account, amount: float, currency: str, when: datetime
) -> tuple[float | None, dict | None]:
    """Montant (devise de `dest`, None si identique) et achat de titres de la jambe créditrice d'un
    virement récurrent arrivant le `when`. Lève CurrencyConversionError sans taux disponible."""
    transfer_amount = None
    if dest.currency != account.currency:
        transfer_amount = await convert_amount(amount, account.currency, dest.currency, date=when.date(), db=db)

    trade = None
    if rd.ticker and dest.type == "investissement":
        leg_amount = transfer_amount if transfer_amount is not None else amount
        qty, price, price_cur, invested = await _size_trade(db, rd, dest.currency, leg_amount, currency, when)
        if invested is not None:
            transfer_amount = invested  # parts entières : seul le coût des parts arrive en versement
        trade = {
            "ticker": rd.ticker.upper().strip(),
            "isin": rd.isin.upper().strip() if rd.isin else None,
            "quantity": qty,
            "unit_price": price,
            "price_currency": price_cur,
            "asset_class": rd.asset_class,
            "sector": rd.sector,
            "geographic_zone": rd.geographic_zone,
            "etf_profile_id": rd.etf_profile_id,
        }
    return transfer_amount, trade


async def _credit_pending_transfers(
    db: Session, now: datetime, affected_account_ids: set[int], affected_holding_account_ids: set[int]
) -> int:
    """Crédite les virements récurrents à arrivée différée dont la date d'arrivée est passée.

    Une sortie d'une telle règle reste « en transit » (`transfer_credit_due`) jusqu'à son jour d'arrivée.
    Si elle a été liée entre-temps (contrepartie importée puis rapprochée) ou que sa règle n'a plus de
    destination, l'échéance est simplement levée : jamais deux crédits pour une sortie.
    """
    credited = 0
    for sortie in repo.transfers_due(db, now):
        when = sortie.transfer_credit_due
        rd = db.get(RecurringTransaction, sortie.recurring_transaction_id) if sortie.recurring_transaction_id else None
        dest = db.get(Account, rd.transfer_to_account_id) if rd and rd.transfer_to_account_id else None
        account = db.get(Account, sortie.account_id)
        already_linked = sortie.is_transfer or sortie.linked_transaction_id or sortie.linked_investment_transaction_id
        if not dest or not account or already_linked or sortie.is_transfer_ignored:
            sortie.transfer_credit_due = None
            db.commit()
            continue
        try:
            transfer_amount, trade = await _transfer_credit(db, rd, account, dest, sortie.amount, rd.currency, when)
        except CurrencyConversionError as exc:
            logger.warning(f"Deferring credit of recurring transfer {rd.id} ({when.date()}): {exc}")
            continue
        await create_counterpart(
            db, sortie, dest, date=when, amount=transfer_amount,
            origin="recurring", recurring_transaction_id=rd.id, trade=trade,
        )
        sortie.transfer_credit_due = None
        db.commit()
        credited += 1
        affected_account_ids.add(dest.id)
        if trade:
            affected_holding_account_ids.add(dest.id)
    return credited

@dataclass
class _Generation:
    """Compteurs et comptes à recalculer d'un passage de génération."""
    generated: int = 0
    accounts: set[int] = field(default_factory=set)
    holding_accounts: set[int] = field(default_factory=set)


async def _generate_security_occurrence(db: Session, rd: RecurringTransaction, account: Account, occ: datetime,
                                        amount: float, original_amount: float, inv_type: str, run: _Generation) -> None:
    quantity, unit_price, price_currency, invested = await _size_trade(db, rd, account.currency, amount, rd.currency, occ)
    tx_amount, tx_original = amount, original_amount
    if invested is not None:
        # Parts entières : le montant suit le coût des parts (original_amount au prorata)
        tx_original = round(original_amount * invested / amount, 2) if amount else invested
        tx_amount = invested
    db.add(InvestmentTransaction(
        account_id=rd.account_id,
        date=occ,
        type=inv_type,
        amount=tx_amount,
        currency=rd.currency,
        original_amount=tx_original,
        note=rd.note or rd.name,
        asset_class=rd.asset_class,
        sector=rd.sector,
        geographic_zone=rd.geographic_zone,
        ticker=rd.ticker.upper().strip() if rd.ticker else None,
        isin=rd.isin.upper().strip() if rd.isin else None,
        quantity=quantity,
        unit_price=unit_price,
        price_currency=price_currency,
        etf_profile_id=rd.etf_profile_id,
        recurring_transaction_id=rd.id,
    ))
    if rd.ticker:
        run.holding_accounts.add(rd.account_id)


async def _generate_cash_occurrence(db: Session, rd: RecurringTransaction, account: Account, occ: datetime,
                                    amount: float, run: _Generation) -> bool:
    """Échéance en espèces (et sa contrepartie de virement). False si le crédit ne peut pas être converti."""
    dest = repo.get_account(db, rd.transfer_to_account_id) if rd.transfer_to_account_id else None
    credit = None
    if dest and not rd.transfer_credit_day:
        try:
            credit = await _transfer_credit(db, rd, account, dest, amount, rd.currency, occ)
        except CurrencyConversionError as exc:
            logger.warning(f"Skipping recurring transfer {rd.id} at {occ.date()}: {exc}")
            return False

    new_tx = Transaction(
        account_id=rd.account_id,
        date=occ,
        month_label=month_label_from_date(occ),
        type=rd.type,
        merchant=rd.name,
        category_id=rd.category_id,
        amount=amount,
        currency=rd.currency,
        original_amount=rd.amount,
        running_balance=0.0,
        note=rd.note or rd.name,
        is_recurring=True,
        recurring_transaction_id=rd.id,
        transfer_credit_due=transfer_credit_date(occ, rd.transfer_credit_day) if dest and rd.transfer_credit_day else None,
    )
    db.add(new_tx)
    # Crédit différé : la contrepartie est créée par _credit_pending_transfers au jour d'arrivée
    if credit is not None:
        transfer_amount, trade = credit
        db.flush()
        await create_counterpart(
            db, new_tx, dest, date=occ, amount=transfer_amount,
            origin="recurring", recurring_transaction_id=rd.id, trade=trade,
        )
        run.accounts.add(dest.id)
        if trade:
            run.holding_accounts.add(dest.id)
    return True


async def _generate_occurrence(db: Session, rd: RecurringTransaction, account: Account, occ: datetime,
                               run: _Generation) -> bool:
    """Crée l'opération d'une échéance. False = s'arrêter là (pas de taux) et réessayer plus tard."""
    amount = rd.amount
    if rd.currency != account.currency:
        try:
            amount = await convert_amount(amount=rd.amount, from_currency=rd.currency, to_currency=account.currency,
                                          date=occ.date(), db=db)
        except CurrencyConversionError as exc:
            # Pas de taux : on ne génère rien (et on garde last_generated_date) pour réessayer plus tard
            logger.warning(f"Skipping recurring tx {rd.id} at {occ.date()}: {exc}")
            return False

    is_inv, inv_type = investment_leg_type(rd.type, account.type, bool(rd.ticker), bool(rd.transfer_to_account_id))
    if is_inv and inv_type in ("versement", "retrait", "dividende"):
        await _generate_security_occurrence(db, rd, account, occ, amount, rd.amount, inv_type, run)
    elif not await _generate_cash_occurrence(db, rd, account, occ, amount, run):
        return False
    run.generated += 1
    run.accounts.add(rd.account_id)
    rd.last_generated_date = occ
    return True


async def _generate_rule(db: Session, rd: RecurringTransaction, now: datetime, run: _Generation) -> None:
    # Fenêtre : depuis la dernière génération (exclue) ou le début de la règle
    start_search = rd.last_generated_date + timedelta(seconds=1) if rd.last_generated_date else rd.start_date
    if start_search >= now:
        return
    occurrences = get_recurring_occurrences(rd, start_search, now)
    account = repo.get_account(db, rd.account_id)
    if not account:
        logger.warning(f"Account {rd.account_id} not found for recurring tx {rd.id}. Disabling rule to prevent infinite retries.")
        rd.is_active = False
        if occurrences:
            rd.last_generated_date = occurrences[-1]
        db.commit()
        return
    for occ in occurrences:
        if not await _generate_occurrence(db, rd, account, occ, run):
            break
    db.commit()


async def generate_recurring_transactions(db: Session) -> int:
    """Génère les opérations dues de toutes les récurrences actives ; renvoie le nombre créé."""
    now = datetime.now()
    run = _Generation()
    for rd in repo.generatable_rules(db):
        await _generate_rule(db, rd, now, run)

    run.generated += await _credit_pending_transfers(db, now, run.accounts, run.holding_accounts)
    for acc_id in run.holding_accounts:
        await rebuild_holdings(db, acc_id)
    if run.holding_accounts:
        db.commit()

    if run.generated > 0:
        for acc_id in run.accounts:
            recalculate_running_balances(db, acc_id)
        db.commit()
        await auto_link_transfers(db)
        logger.info(f"Generated {run.generated} recurring transactions")
    return run.generated
