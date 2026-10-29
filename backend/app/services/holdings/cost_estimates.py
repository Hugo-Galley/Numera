"""Estimation du PRU des lignes d'inventaire Point Zéro depuis les achats saisis avant sa date."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.dividends import match_dividend_ticker
from app.domain.holdings import EPSILON, SELL_TYPES, CostEstimate, normalize_ticker
from app.models.holding_baseline_item import HoldingBaselineItem
from app.models.investment_transaction import InvestmentTransaction
from app.repositories import holdings as repo
from app.repositories import investment_transactions as tx_repo
from app.services.holdings.replay import convert, trade_cutoff


def _amount_only_buys(db: Session, account_id: int, items: list[HoldingBaselineItem]) -> dict[str, list[InvestmentTransaction]]:
    """Anciens versements « Achat Apple » : ni titre ni quantité, seulement un montant et un libellé."""
    candidates = [(i.ticker, i.asset_name) for i in items]
    amount_only: dict[str, list[InvestmentTransaction]] = {}
    for tx in tx_repo.buys(db, account_id):
        if tx.ticker and tx.quantity and tx.quantity > 0:
            continue
        ticker = normalize_ticker(tx.ticker) if tx.ticker else match_dividend_ticker(tx.note, candidates)
        if ticker:
            amount_only.setdefault(ticker, []).append(tx)
    return amount_only


async def _from_trades(db: Session, account_id: int, item: HoldingBaselineItem) -> tuple[float, float, float, float, int, datetime | None]:
    """Coût total, quantités achetée / vendue / valorisée, nombre d'achats et premier achat avant l'inventaire."""
    cutoff = trade_cutoff(db, account_id, item.ticker) or item.baseline_date
    total_cost = bought = sold = 0.0
    priced_qty = 0.0
    buys = 0
    first_buy = None
    for tx in tx_repo.trades(db, account_id, until=cutoff):
        if normalize_ticker(tx.ticker) != item.ticker:
            continue
        if tx.type in SELL_TYPES:
            sold += tx.quantity
            continue
        buys += 1
        bought += tx.quantity
        first_buy = first_buy or tx.date
        if tx.unit_price:
            gross, cur = tx.quantity * tx.unit_price + (tx.fees or 0.0), (tx.price_currency or tx.currency or "EUR").upper()
        elif tx.original_amount:
            gross, cur = tx.original_amount, (tx.currency or "EUR").upper()
        else:
            continue
        converted = gross if cur == item.currency else await convert(db, gross, cur, item.currency, tx.date)
        if converted is None:
            continue
        total_cost += converted
        priced_qty += tx.quantity
    return total_cost, bought, sold, priced_qty, buys, first_buy


async def _estimate_item(db: Session, account_id: int, item: HoldingBaselineItem, amount_only: list[InvestmentTransaction]) -> CostEstimate:
    total_cost, bought, sold, priced_qty, buys, first_buy = await _from_trades(db, account_id, item)
    method = "quantities"
    estimate = round(total_cost / priced_qty, 4) if priced_qty > EPSILON else None
    cutoff_date = trade_cutoff(db, account_id, item.ticker) or item.baseline_date
    extra = [t for t in amount_only if t.date <= cutoff_date]
    if extra and item.quantity > EPSILON:
        # Quantités inconnues : on suppose que ces versements ont financé toutes les parts de l'inventaire
        for tx in extra:
            cur = (tx.currency or "EUR").upper()
            converted = tx.original_amount if cur == item.currency else await convert(db, tx.original_amount, cur, item.currency, tx.date)
            if converted is not None:
                total_cost += converted
                first_buy = min(first_buy, tx.date) if first_buy else tx.date
        estimate = round(total_cost / item.quantity, 4)
        method = "amounts"
    return CostEstimate(
        ticker=item.ticker,
        asset_name=item.asset_name,
        quantity=item.quantity,
        currency=item.currency,
        current_cost=item.buy_price_avg,
        estimate=estimate,
        buys=buys + len(extra),
        method=method,
        amount_only_buys=len(extra),
        bought_quantity=bought,
        sold_quantity=sold,
        first_buy=first_buy,
    )


async def estimate_baseline_costs(db: Session, account_id: int) -> list[CostEstimate]:
    """Estime le PRU de chaque ligne d'inventaire depuis les achats saisis avant la date du Point Zéro.

    Ce sont exactement les opérations que l'inventaire « remplace » : leurs prix et quantités restent
    en base et permettent de retrouver le coût moyen (moyenne pondérée, frais inclus). Aucune écriture.
    """
    items = repo.baseline_items(db, account_id, order_by_id=True)
    amount_only = _amount_only_buys(db, account_id, items)
    return [await _estimate_item(db, account_id, item, amount_only.get(item.ticker, [])) for item in items]
