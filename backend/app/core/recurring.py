from datetime import datetime
from sqlalchemy.orm import Session
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.investment_transaction import InvestmentTransaction
from app.core.finance import get_recurring_occurrences, month_label_from_date
from app.core.currency import CurrencyConversionError, convert_amount
from app.core.holdings import rebuild_holdings
from app.core.transfers import auto_link_transfers, create_counterpart
from app.core.logging import get_logger

logger = get_logger(__name__)


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

        from app.models.account import Account
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

            is_inv = account.type in ["investissement", "assurance_vie"] or bool(rd.ticker)
            inv_type = rd.type.lower()
            if inv_type in ["sortie", "achat"]:
                inv_type = "versement"
            elif inv_type in ["entree", "vente"]:
                inv_type = "retrait"

            if is_inv and inv_type in ["versement", "retrait", "dividende"]:
                effective_unit_price = rd.unit_price
                effective_quantity = rd.quantity
                # Prix fixé dans la règle : exprimé dans la devise de la règle
                price_currency = currency if effective_unit_price else None

                # Quantité ou prix non fixés : on part du cours du titre, dans sa devise de cotation
                if rd.ticker and (not effective_quantity or effective_quantity <= 0 or not effective_unit_price):
                    norm_ticker = rd.ticker.upper().strip()
                    try:
                        from app.core.market_data import get_market_quotes
                        quotes = await get_market_quotes([norm_ticker], db=db)
                        q_data = quotes.get(norm_ticker, {})
                        if q_data.get("price") and float(q_data["price"]) > 0:
                            effective_unit_price = round(float(q_data["price"]), 4)
                            price_currency = q_data.get("currency") or account.currency
                    except Exception as e:
                        logger.warning(f"Could not fetch live quote for recurring tx {rd.id} ({norm_ticker}): {e}")

                # Automatically compute shares if not explicitly fixed
                if (not effective_quantity or effective_quantity <= 0) and effective_unit_price and effective_unit_price > 0:
                    try:
                        price_in_account = await convert_amount(
                            effective_unit_price, price_currency or account.currency, account.currency, date=occ.date(), db=db
                        )
                        effective_quantity = round(converted_amount / price_in_account, 6)
                    except CurrencyConversionError as exc:
                        logger.warning(f"Recurring tx {rd.id}: cannot size the trade ({exc})")
                elif effective_quantity and (not effective_unit_price or effective_unit_price <= 0) and converted_amount > 0:
                    effective_unit_price = round(converted_amount / effective_quantity, 4)
                    price_currency = account.currency

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
                transfer_amount = None
                if rd.transfer_to_account_id:
                    transfer_dest = db.query(Account).filter(Account.id == rd.transfer_to_account_id).first()
                    if transfer_dest and transfer_dest.currency != account.currency:
                        try:
                            transfer_amount = await convert_amount(
                                converted_amount, account.currency, transfer_dest.currency, date=occ.date(), db=db
                            )
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
                )
                db.add(new_tx)
                if transfer_dest:
                    db.flush()
                    await create_counterpart(
                        db, new_tx, transfer_dest, date=occ, amount=transfer_amount,
                        origin="recurring", recurring_transaction_id=rd.id,
                    )
                    affected_account_ids.add(transfer_dest.id)
            generated_count += 1
            affected_account_ids.add(rd.account_id)

            # Update last_generated_date
            rd.last_generated_date = occ

        db.commit()

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
