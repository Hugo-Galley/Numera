"""Rejeu des positions d'un compte : inventaire Point Zéro puis opérations sur titres postérieures.

Source unique de la logique : toute création / modification / suppression d'opération, la génération
des récurrences et l'édition de l'inventaire appellent `rebuild_holdings` (`services/holdings/rebuild.py`),
qui recalcule intégralement les positions d'un compte (même principe que `recalculate_running_balances`).

Pour chaque ticker, on part de la ligne d'inventaire (`holding_baseline_items`) si elle existe, puis on
rejoue dans l'ordre chronologique les opérations postérieures à la date du Point Zéro :
- `achat` / `versement` avec titre : augmente la quantité ; le coût (quantité × prix + frais) s'ajoute,
  d'où un PRU en moyenne pondérée, frais inclus ;
- `vente` / `retrait` avec titre : diminue la quantité ; le coût baisse au prorata, le PRU ne change pas ;
- `dividende`, `frais` : aucun effet sur la position.

Le PRU est exprimé dans la devise de la position ; `cost_basis_eur` cumule les coûts convertis en EUR
au taux du jour de chaque achat (taux du Point Zéro pour l'inventaire).
"""
from dataclasses import replace
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.holdings import BUY_TYPES, EPSILON, SELL_TYPES, Position, RealizedSale, Replay, normalize_ticker
from app.integrations.currency import CurrencyConversionError, convert_amount
from app.models.investment_transaction import InvestmentTransaction
from app.repositories import holdings as repo
from app.repositories import investment_transactions as tx_repo

logger = get_logger(__name__)


def trade_cutoff(db: Session, account_id: int, ticker: str) -> datetime | None:
    """Date jusqu'à laquelle les opérations sur `ticker` sont couvertes par l'inventaire Point Zéro."""
    account = repo.account(db, account_id)
    dates = [account.holdings_baseline_date] if account and account.holdings_baseline_date else []
    item = repo.baseline_item(db, account_id, normalize_ticker(ticker))
    if item:
        dates.append(item.baseline_date)
    return max(dates) if dates else None


async def convert(db: Session, amount: float, from_cur: str, to_cur: str, when: datetime) -> float | None:
    try:
        return await convert_amount(amount, from_cur, to_cur, date=when.date(), db=db)
    except CurrencyConversionError as exc:
        logger.warning(f"Holdings rebuild: {exc}")
        return None


async def _load_baseline(db: Session, account_id: int, account_cutoff: datetime | None) -> tuple[dict[str, Position], datetime | None]:
    """Positions de l'inventaire Point Zéro et date du Point Zéro du compte."""
    positions: dict[str, Position] = {}
    items = repo.baseline_items(db, account_id)
    for item in items:
        cost = item.quantity * item.buy_price_avg if item.buy_price_avg else None
        positions[item.ticker] = Position(
            ticker=item.ticker,
            currency=item.currency,
            quantity=item.quantity,
            cost=cost,
            cost_eur=await convert(db, cost, item.currency, "EUR", item.baseline_date) if cost else None,
            isin=item.isin,
            asset_name=item.asset_name,
            etf_profile_id=item.etf_profile_id,
            cutoff=max(d for d in (account_cutoff, item.baseline_date) if d is not None),
        )
    baseline_dates = [i.baseline_date for i in items]
    return positions, account_cutoff or (max(baseline_dates) if baseline_dates else None)


async def _apply_buy(db: Session, pos: Position, tx: InvestmentTransaction, price_currency: str) -> None:
    if tx.unit_price:
        gross = tx.quantity * tx.unit_price + (tx.fees or 0.0)
        if pos.cost is not None:
            added = gross if price_currency == pos.currency else await convert(db, gross, price_currency, pos.currency, tx.date)
            pos.cost = None if added is None else pos.cost + added
        if pos.cost_eur is not None:
            added_eur = await convert(db, gross, price_currency, "EUR", tx.date)
            pos.cost_eur = None if added_eur is None else pos.cost_eur + added_eur
    elif pos.quantity > EPSILON and pos.cost is not None:
        # Prix inconnu : on suppose l'achat au PRU courant (le PRU ne bouge pas)
        ratio = (pos.quantity + tx.quantity) / pos.quantity
        pos.cost *= ratio
        pos.cost_eur = pos.cost_eur * ratio if pos.cost_eur is not None else None
    else:
        pos.cost = pos.cost_eur = None
    pos.quantity += tx.quantity


async def _apply_sell(db: Session, pos: Position, tx: InvestmentTransaction, ticker: str, price_currency: str) -> RealizedSale | None:
    """Vend au plus la quantité détenue ; renvoie la vente réalisée (None si rien n'était détenu)."""
    sold = min(tx.quantity, pos.quantity)
    ratio = (pos.quantity - sold) / pos.quantity if pos.quantity > EPSILON else 0.0
    sale = None
    if sold > EPSILON:
        share = sold / tx.quantity
        if tx.unit_price:
            net = tx.quantity * tx.unit_price - (tx.fees or 0.0)
            proceeds_eur = await convert(db, net * share, price_currency, "EUR", tx.date)
        else:
            proceeds_eur = await convert(db, tx.original_amount * share, tx.currency, "EUR", tx.date)
        sale = RealizedSale(
            tx_id=tx.id,
            date=tx.date,
            ticker=ticker,
            quantity=sold,
            proceeds_eur=proceeds_eur,
            cost_eur=pos.cost_eur * (1 - ratio) if pos.cost_eur is not None else None,
        )
    pos.cost = pos.cost * ratio if pos.cost is not None else None
    pos.cost_eur = pos.cost_eur * ratio if pos.cost_eur is not None else None
    pos.quantity -= sold
    if pos.quantity <= EPSILON:
        # Position soldée : un rachat ultérieur repart d'un coût nul (PRU de nouveau calculable)
        pos.quantity, pos.cost, pos.cost_eur = 0.0, 0.0, 0.0
    return sale


async def replay_account(db: Session, account_id: int) -> Replay:
    """Rejoue l'inventaire Point Zéro puis les opérations sur titres (aucune écriture)."""
    account = repo.account(db, account_id)
    account_cutoff = account.holdings_baseline_date if account else None
    positions, baseline_date = await _load_baseline(db, account_id, account_cutoff)
    baseline = {t: replace(p) for t, p in positions.items()}
    realized: list[RealizedSale] = []
    events: list[tuple[datetime, str, float]] = []

    for tx in tx_repo.trades(db, account_id):
        ticker = normalize_ticker(tx.ticker)
        pos = positions.get(ticker)
        cutoff = pos.cutoff if pos else account_cutoff
        if cutoff and tx.date <= cutoff:
            continue  # couvert par l'inventaire Point Zéro

        price_currency = (tx.price_currency or tx.currency or "EUR").upper()
        if pos is None:
            if tx.type in SELL_TYPES:
                logger.warning(f"Holdings rebuild: sale of {ticker} without position (tx {tx.id}) ignored")
                continue
            pos = positions[ticker] = Position(ticker=ticker, currency=price_currency, cutoff=account_cutoff)
        pos.isin = pos.isin or tx.isin
        pos.asset_name = pos.asset_name or tx.note
        pos.etf_profile_id = pos.etf_profile_id or tx.etf_profile_id

        if tx.type in BUY_TYPES:
            await _apply_buy(db, pos, tx, price_currency)
            events.append((tx.date, ticker, tx.quantity))
        else:
            sale = await _apply_sell(db, pos, tx, ticker, price_currency)
            if sale is not None:
                realized.append(sale)
                events.append((tx.date, ticker, -sale.quantity))

    return Replay(positions=positions, realized=realized, baseline_date=baseline_date, baseline=baseline, quantity_events=events)
