"""Positions (`portfolio_holdings`) dérivées de l'inventaire Point Zéro et des opérations sur titres.

Source unique de la logique : toute création / modification / suppression d'opération, la génération
des récurrences et l'édition de l'inventaire appellent `rebuild_holdings`, qui recalcule intégralement
les positions d'un compte (même principe que `recalculate_running_balances`).

Pour chaque ticker, on part de la ligne d'inventaire (`holding_baseline_items`) si elle existe, puis on
rejoue dans l'ordre chronologique les opérations postérieures à la date du Point Zéro :
- `achat` / `versement` avec titre : augmente la quantité ; le coût (quantité × prix + frais) s'ajoute,
  d'où un PRU en moyenne pondérée, frais inclus ;
- `vente` / `retrait` avec titre : diminue la quantité ; le coût baisse au prorata, le PRU ne change pas ;
- `dividende`, `frais` : aucun effet sur la position.

Le PRU est exprimé dans la devise de la position ; `cost_basis_eur` cumule les coûts convertis en EUR
au taux du jour de chaque achat (taux du Point Zéro pour l'inventaire).
"""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.currency import CurrencyConversionError, convert_amount
from app.core.logging import get_logger
from app.models.account import Account
from app.models.holding_baseline_item import HoldingBaselineItem
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding

logger = get_logger(__name__)

BUY_TYPES = ("versement", "achat")
SELL_TYPES = ("retrait", "vente")
TRADE_TYPES = BUY_TYPES + SELL_TYPES
EPSILON = 1e-9


def normalize_ticker(ticker: str) -> str:
    return ticker.upper().strip()


def is_trade(tx_type: str, ticker: str | None, quantity: float | None) -> bool:
    """Vrai si l'opération fait bouger une position (titre + quantité + type achat/vente)."""
    return bool(ticker) and bool(quantity) and quantity > 0 and tx_type in TRADE_TYPES


def trade_cutoff(db: Session, account_id: int, ticker: str) -> datetime | None:
    """Date jusqu'à laquelle les opérations sur `ticker` sont couvertes par l'inventaire Point Zéro."""
    account = db.get(Account, account_id)
    dates = [account.holdings_baseline_date] if account and account.holdings_baseline_date else []
    item = (
        db.query(HoldingBaselineItem)
        .filter(HoldingBaselineItem.account_id == account_id, HoldingBaselineItem.ticker == normalize_ticker(ticker))
        .first()
    )
    if item:
        dates.append(item.baseline_date)
    return max(dates) if dates else None


@dataclass
class _Position:
    ticker: str
    currency: str
    quantity: float = 0.0
    cost: float | None = 0.0  # devise de la position ; None = PRU inconnu
    cost_eur: float | None = 0.0
    isin: str | None = None
    asset_name: str | None = None
    etf_profile_id: int | None = None
    cutoff: datetime | None = None


async def _convert(db: Session, amount: float, from_cur: str, to_cur: str, when: datetime) -> float | None:
    try:
        return await convert_amount(amount, from_cur, to_cur, date=when.date(), db=db)
    except CurrencyConversionError as exc:
        logger.warning(f"Holdings rebuild: {exc}")
        return None


async def rebuild_holdings(db: Session, account_id: int) -> None:
    """Recalcule toutes les positions du compte depuis l'inventaire et les opérations. Ne commit pas."""
    account = db.get(Account, account_id)
    account_cutoff = account.holdings_baseline_date if account else None
    positions: dict[str, _Position] = {}

    for item in db.query(HoldingBaselineItem).filter(HoldingBaselineItem.account_id == account_id).all():
        cost = item.quantity * item.buy_price_avg if item.buy_price_avg else None
        positions[item.ticker] = _Position(
            ticker=item.ticker,
            currency=item.currency,
            quantity=item.quantity,
            cost=cost,
            cost_eur=await _convert(db, cost, item.currency, "EUR", item.baseline_date) if cost else None,
            isin=item.isin,
            asset_name=item.asset_name,
            etf_profile_id=item.etf_profile_id,
            cutoff=max(d for d in (account_cutoff, item.baseline_date) if d is not None),
        )

    trades = (
        db.query(InvestmentTransaction)
        .filter(
            InvestmentTransaction.account_id == account_id,
            InvestmentTransaction.ticker.isnot(None),
            InvestmentTransaction.quantity > 0,
            InvestmentTransaction.type.in_(TRADE_TYPES),
        )
        .order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc())
        .all()
    )
    for tx in trades:
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
            pos = positions[ticker] = _Position(ticker=ticker, currency=price_currency, cutoff=account_cutoff)
        pos.isin = pos.isin or tx.isin
        pos.asset_name = pos.asset_name or tx.note
        pos.etf_profile_id = pos.etf_profile_id or tx.etf_profile_id

        if tx.type in BUY_TYPES:
            if tx.unit_price:
                gross = tx.quantity * tx.unit_price + (tx.fees or 0.0)
                if pos.cost is not None:
                    added = gross if price_currency == pos.currency else await _convert(db, gross, price_currency, pos.currency, tx.date)
                    pos.cost = None if added is None else pos.cost + added
                if pos.cost_eur is not None:
                    added_eur = await _convert(db, gross, price_currency, "EUR", tx.date)
                    pos.cost_eur = None if added_eur is None else pos.cost_eur + added_eur
            elif pos.quantity > EPSILON and pos.cost is not None:
                # Prix inconnu : on suppose l'achat au PRU courant (le PRU ne bouge pas)
                ratio = (pos.quantity + tx.quantity) / pos.quantity
                pos.cost *= ratio
                pos.cost_eur = pos.cost_eur * ratio if pos.cost_eur is not None else None
            else:
                pos.cost = pos.cost_eur = None
            pos.quantity += tx.quantity
        else:
            sold = min(tx.quantity, pos.quantity)
            ratio = (pos.quantity - sold) / pos.quantity if pos.quantity > EPSILON else 0.0
            pos.cost = pos.cost * ratio if pos.cost is not None else None
            pos.cost_eur = pos.cost_eur * ratio if pos.cost_eur is not None else None
            pos.quantity -= sold
            if pos.quantity <= EPSILON:
                # Position soldée : un rachat ultérieur repart d'un coût nul (PRU de nouveau calculable)
                pos.quantity, pos.cost, pos.cost_eur = 0.0, 0.0, 0.0

    existing = {h.ticker: h for h in db.query(PortfolioHolding).filter(PortfolioHolding.account_id == account_id).all()}
    for ticker, holding in existing.items():
        pos = positions.get(ticker)
        if pos is None or pos.quantity <= EPSILON:
            db.delete(holding)

    for ticker, pos in positions.items():
        if pos.quantity <= EPSILON:
            continue
        pru = round(pos.cost / pos.quantity, 4) if pos.cost else None
        cost_eur = round(pos.cost_eur, 2) if pos.cost_eur else None
        holding = existing.get(ticker)
        if holding is None:
            db.add(
                PortfolioHolding(
                    account_id=account_id,
                    ticker=ticker,
                    isin=pos.isin.upper().strip() if pos.isin else None,
                    asset_name=pos.asset_name or ticker,
                    quantity=pos.quantity,
                    buy_price_avg=pru,
                    currency=pos.currency,
                    cost_basis_eur=cost_eur,
                    etf_profile_id=pos.etf_profile_id,
                )
            )
        else:
            holding.quantity = pos.quantity
            holding.buy_price_avg = pru
            holding.currency = pos.currency
            holding.cost_basis_eur = cost_eur
            holding.isin = holding.isin or pos.isin
            holding.etf_profile_id = holding.etf_profile_id or pos.etf_profile_id
    db.flush()
