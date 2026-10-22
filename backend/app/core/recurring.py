import calendar
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.investment_transaction import InvestmentTransaction
from app.core.finance import get_recurring_occurrences, month_label_from_date
from app.core.currency import CurrencyConversionError, convert_amount
from app.core import market_data
from app.core.holdings import rebuild_holdings
from app.core.transfers import auto_link_transfers, create_counterpart
from app.core.logging import get_logger

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
) -> tuple[float | None, float | None, str | None]:
    """Quantité, prix unitaire et devise du prix d'un achat récurrent de `amount` (devise du compte).

    Quantité et prix fixés dans la règle : repris tels quels. Sinon le prix vient du cours de clôture
    à la date de l'échéance (devise de cotation) et la quantité = montant ÷ prix.
    """
    unit_price = rd.unit_price
    quantity = rd.quantity
    price_currency = currency if unit_price else None  # prix fixé dans la règle : devise de la règle

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
            quantity = round(amount / price_in_account, 6)
        except CurrencyConversionError as exc:
            logger.warning(f"Recurring tx {rd.id}: cannot size the trade ({exc})")
    elif quantity and (not unit_price or unit_price <= 0) and amount > 0:
        unit_price = round(amount / quantity, 4)
        price_currency = account_currency
    return quantity, unit_price, price_currency


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
        qty, price, price_cur = await _size_trade(db, rd, dest.currency, leg_amount, currency, when)
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
    due = db.query(Transaction).filter(
        Transaction.transfer_credit_due.isnot(None), Transaction.transfer_credit_due <= now
    ).order_by(Transaction.transfer_credit_due).all()
    credited = 0
    for sortie in due:
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

async def generate_recurring_transactions(db: Session) -> int:
    """
    Check all active recurring transactions and generate pending real transactions.
    Returns the number of transactions generated.

    NOTE: Salary-managed recurring transactions (linked to SalaryConfig) are
    excluded here. They are handled exclusively by app.core.salary to avoid
    the double-generation bug that created hundreds of duplicate salary entries.
    """
    now = datetime.now()

    recurring_defs = db.query(RecurringTransaction).filter(
        RecurringTransaction.is_active == True,
        RecurringTransaction.auto_generate == True,
    ).all()

    # Exclude salary-managed recurring transactions entirely.
    # These are managed by check_and_generate_pending_salaries() instead.
    from app.models.salary_config import SalaryConfig
    salary_managed_ids: set[int] = set()
    for sc in db.query(SalaryConfig).filter(SalaryConfig.is_active == True).all():
        if sc.salary_recurring_id:
            salary_managed_ids.add(sc.salary_recurring_id)
        if sc.ticket_recurring_id:
            salary_managed_ids.add(sc.ticket_recurring_id)

    recurring_defs = [rd for rd in recurring_defs if rd.id not in salary_managed_ids]

    generated_count = 0
    affected_account_ids: set[int] = set()
    affected_holding_account_ids: set[int] = set()

    for rd in recurring_defs:
        # Determine the search window start
        start_search = rd.last_generated_date if rd.last_generated_date else rd.start_date

        # Avoid double counting the last generated date
        if rd.last_generated_date:
            from datetime import timedelta
            start_search = start_search + timedelta(seconds=1)

        if start_search >= now:
            continue

        occurrences = get_recurring_occurrences(rd, start_search, now)

        account = db.query(Account).filter(Account.id == rd.account_id).first()
        if not account:
            logger.warning(f"Account {rd.account_id} not found for recurring tx {rd.id}. Disabling rule to prevent infinite retries.")
            rd.is_active = False
            if occurrences:
                rd.last_generated_date = occurrences[-1]
            db.commit()
            continue

        for occ in occurrences:

            original_amount = rd.amount
            currency = rd.currency
            note = rd.note or rd.name

            if currency != account.currency:
                try:
                    converted_amount = await convert_amount(
                        amount=original_amount,
                        from_currency=currency,
                        to_currency=account.currency,
                        date=occ.date(),
                        db=db,
                    )
                except CurrencyConversionError as exc:
                    # Pas de taux : on ne génère rien (et on garde last_generated_date) pour réessayer plus tard
                    logger.warning(f"Skipping recurring tx {rd.id} at {occ.date()}: {exc}")
                    break
            else:
                converted_amount = original_amount

            is_investment_account = account.type in ["investissement", "assurance_vie"]
            is_inv = is_investment_account or (bool(rd.ticker) and not rd.transfer_to_account_id)
            inv_type = rd.type.lower()
            if inv_type in ["achat", "vente"]:
                inv_type = "versement" if inv_type == "achat" else "retrait"
            elif is_investment_account and inv_type in ["entree", "sortie"]:
                # Règle posée sur le compte investissement lui-même : une Entrée y fait entrer l'argent
                inv_type = "versement" if inv_type == "entree" else "retrait"
            elif inv_type in ["sortie", "entree"]:
                # Achat programmé depuis un compte bancaire (ticker) : la Sortie finance l'achat
                inv_type = "versement" if inv_type == "sortie" else "retrait"

            if is_inv and inv_type in ["versement", "retrait", "dividende"]:
                effective_quantity, effective_unit_price, price_currency = await _size_trade(
                    db, rd, account.currency, converted_amount, currency, occ
                )

                new_tx = InvestmentTransaction(
                    account_id=rd.account_id,
                    date=occ,
                    type=inv_type,
                    amount=converted_amount,
                    currency=currency,
                    original_amount=original_amount,
                    note=note,
                    asset_class=rd.asset_class,
                    sector=rd.sector,
                    geographic_zone=rd.geographic_zone,
                    ticker=rd.ticker.upper().strip() if rd.ticker else None,
                    isin=rd.isin.upper().strip() if rd.isin else None,
                    quantity=effective_quantity,
                    unit_price=effective_unit_price,
                    price_currency=price_currency,
                    etf_profile_id=rd.etf_profile_id,
                    recurring_transaction_id=rd.id,
                )
                db.add(new_tx)
                if rd.ticker:
                    affected_holding_account_ids.add(rd.account_id)
            else:
                # Virement vers un autre compte : on convertit avant de créer quoi que ce soit
                transfer_dest = None
                credit = None
                if rd.transfer_to_account_id:
                    transfer_dest = db.query(Account).filter(Account.id == rd.transfer_to_account_id).first()
                if transfer_dest and not rd.transfer_credit_day:
                    try:
                        credit = await _transfer_credit(db, rd, account, transfer_dest, converted_amount, currency, occ)
                    except CurrencyConversionError as exc:
                        logger.warning(f"Skipping recurring transfer {rd.id} at {occ.date()}: {exc}")
                        break

                new_tx = Transaction(
                    account_id=rd.account_id,
                    date=occ,
                    month_label=month_label_from_date(occ),
                    type=rd.type,
                    merchant=rd.name,
                    category_id=rd.category_id,
                    amount=converted_amount,
                    currency=currency,
                    original_amount=original_amount,
                    running_balance=0.0,
                    note=note,
                    is_recurring=True,
                    recurring_transaction_id=rd.id,
                    transfer_credit_due=(
                        transfer_credit_date(occ, rd.transfer_credit_day) if transfer_dest and rd.transfer_credit_day else None
                    ),
                )
                db.add(new_tx)
                # Crédit différé : la contrepartie est créée par _credit_pending_transfers au jour d'arrivée
                if credit is not None:
                    transfer_amount, trade = credit
                    db.flush()
                    await create_counterpart(
                        db, new_tx, transfer_dest, date=occ, amount=transfer_amount,
                        origin="recurring", recurring_transaction_id=rd.id, trade=trade,
                    )
                    affected_account_ids.add(transfer_dest.id)
                    if trade:
                        affected_holding_account_ids.add(transfer_dest.id)
            generated_count += 1
            affected_account_ids.add(rd.account_id)

            # Update last_generated_date
            rd.last_generated_date = occ

        db.commit()

    generated_count += await _credit_pending_transfers(db, now, affected_account_ids, affected_holding_account_ids)

    for acc_id in affected_holding_account_ids:
        await rebuild_holdings(db, acc_id)
    if affected_holding_account_ids:
        db.commit()

    if generated_count > 0:
        # Recalculate balances
        from app.api.transactions import recalculate_running_balances
        for acc_id in affected_account_ids:
            recalculate_running_balances(db, acc_id)
        await auto_link_transfers(db)
        logger.info(f"Generated {generated_count} recurring transactions")

    return generated_count
