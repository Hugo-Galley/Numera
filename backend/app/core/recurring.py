from datetime import datetime
from sqlalchemy.orm import Session
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.investment_transaction import InvestmentTransaction
from app.core.finance import get_recurring_occurrences, month_label_from_date
from app.core.currency import convert_amount
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
                converted_amount = await convert_amount(
                    amount=original_amount,
                    from_currency=currency,
                    to_currency=account.currency,
                    date=occ.date(),
                    db=db,
                )
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

                # If quantity or price is not fixed, fetch live market quote to calculate dynamic shares
                if rd.ticker and (not effective_quantity or effective_quantity <= 0 or not effective_unit_price):
                    norm_ticker = rd.ticker.upper().strip()
                    try:
                        from app.core.market_data import get_market_quotes
                        quotes = await get_market_quotes([norm_ticker])
                        q_data = quotes.get(norm_ticker, {})
                        live_price = q_data.get("price_eur") or q_data.get("price")
                        if live_price and float(live_price) > 0:
                            effective_unit_price = round(float(live_price), 4)
                    except Exception as e:
                        logger.warning(f"Could not fetch live quote for recurring tx {rd.id} ({norm_ticker}): {e}")

                # Automatically compute shares if not explicitly fixed
                if (not effective_quantity or effective_quantity <= 0) and effective_unit_price and effective_unit_price > 0:
                    effective_quantity = round(converted_amount / effective_unit_price, 6)
                elif effective_quantity and (not effective_unit_price or effective_unit_price <= 0) and converted_amount > 0:
                    effective_unit_price = round(converted_amount / effective_quantity, 4)

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
                    etf_profile_id=rd.etf_profile_id,
                    recurring_transaction_id=rd.id,
                )
                db.add(new_tx)

                # Automatic hook: update or create PortfolioHolding if ticker and quantity are provided
                if rd.ticker and effective_quantity and effective_quantity > 0:
                    from app.models.portfolio_holding import PortfolioHolding
                    norm_ticker = rd.ticker.upper().strip()
                    holding = db.query(PortfolioHolding).filter(
                        PortfolioHolding.account_id == rd.account_id,
                        PortfolioHolding.ticker == norm_ticker
                    ).first()
                    qty_delta = effective_quantity if inv_type in ("versement", "achat") else -effective_quantity
                    if holding:
                        # Recalculate average buy price if purchasing more
                        if qty_delta > 0 and effective_unit_price and holding.quantity > 0:
                            old_cost = holding.quantity * (holding.buy_price_avg or effective_unit_price)
                            new_cost = qty_delta * effective_unit_price
                            new_total_qty = holding.quantity + qty_delta
                            holding.buy_price_avg = round((old_cost + new_cost) / new_total_qty, 4) if new_total_qty > 0 else effective_unit_price
                        elif qty_delta > 0 and effective_unit_price:
                            holding.buy_price_avg = effective_unit_price
                        holding.quantity = max(0.0, holding.quantity + qty_delta)
                    elif qty_delta > 0:
                        new_holding = PortfolioHolding(
                            account_id=rd.account_id,
                            ticker=norm_ticker,
                            isin=rd.isin.upper().strip() if rd.isin else None,
                            asset_name=note or norm_ticker,
                            quantity=qty_delta,
                            buy_price_avg=effective_unit_price,
                            currency=currency,
                            etf_profile_id=rd.etf_profile_id,
                        )
                        db.add(new_holding)
            else:
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
            generated_count += 1
            affected_account_ids.add(rd.account_id)

            # Update last_generated_date
            rd.last_generated_date = occ

        db.commit()

    if generated_count > 0:
        # Recalculate balances
        from app.api.transactions import recalculate_running_balances
        for acc_id in affected_account_ids:
            recalculate_running_balances(db, acc_id)
        logger.info(f"Generated {generated_count} recurring transactions")

    return generated_count
