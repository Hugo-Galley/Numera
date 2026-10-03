"""Mise à jour des positions (`portfolio_holdings`) à partir des mouvements de titres.

Source unique de la logique, utilisée par la création / modification / suppression de
transactions d'investissement et par la génération des récurrences.

- `versement` / `achat` : augmente la quantité, recalcule le PRU en moyenne pondérée.
- `retrait` / `vente` : diminue la quantité, le PRU ne change pas.
- `dividende` : aucun effet sur la position.
"""
from sqlalchemy.orm import Session

from app.models.portfolio_holding import PortfolioHolding

BUY_TYPES = ("versement", "achat")
SELL_TYPES = ("retrait", "vente")


def _signed_quantity(tx_type: str, quantity: float) -> float:
    if tx_type in BUY_TYPES:
        return quantity
    if tx_type in SELL_TYPES:
        return -quantity
    return 0.0  # dividende & co : la position ne bouge pas


def _find_holding(db: Session, account_id: int, ticker: str) -> PortfolioHolding | None:
    return (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.account_id == account_id, PortfolioHolding.ticker == ticker)
        .first()
    )


def apply_trade_to_holding(
    db: Session,
    *,
    account_id: int,
    ticker: str | None,
    tx_type: str,
    quantity: float | None,
    unit_price: float | None,
    isin: str | None = None,
    asset_name: str | None = None,
    currency: str = "EUR",
    etf_profile_id: int | None = None,
) -> None:
    """Applique un mouvement à la position du ticker (la crée sur un achat si besoin)."""
    if not ticker or not quantity or quantity <= 0:
        return
    delta = _signed_quantity(tx_type, quantity)
    if delta == 0:
        return

    norm_ticker = ticker.upper().strip()
    holding = _find_holding(db, account_id, norm_ticker)

    if holding is None:
        if delta > 0:
            db.add(
                PortfolioHolding(
                    account_id=account_id,
                    ticker=norm_ticker,
                    isin=isin.upper().strip() if isin else None,
                    asset_name=asset_name or norm_ticker,
                    quantity=delta,
                    buy_price_avg=unit_price,
                    currency=currency,
                    etf_profile_id=etf_profile_id,
                )
            )
        return

    if delta > 0 and unit_price:
        if holding.quantity > 0 and holding.buy_price_avg:
            total_cost = holding.quantity * holding.buy_price_avg + delta * unit_price
            holding.buy_price_avg = round(total_cost / (holding.quantity + delta), 4)
        else:
            holding.buy_price_avg = unit_price
    holding.quantity = max(0.0, holding.quantity + delta)


def reverse_trade_from_holding(
    db: Session,
    *,
    account_id: int,
    ticker: str | None,
    tx_type: str,
    quantity: float | None,
    unit_price: float | None,
) -> None:
    """Annule l'effet d'un mouvement déjà appliqué (suppression / modification)."""
    if not ticker or not quantity or quantity <= 0:
        return
    delta = _signed_quantity(tx_type, quantity)
    if delta == 0:
        return

    holding = _find_holding(db, account_id, ticker.upper().strip())
    if holding is None:
        return

    new_quantity = max(0.0, holding.quantity - delta)
    if delta > 0 and unit_price and holding.buy_price_avg and new_quantity > 0:
        # On retire la contribution de l'achat au PRU pondéré
        remaining_cost = holding.quantity * holding.buy_price_avg - delta * unit_price
        if remaining_cost > 0:
            holding.buy_price_avg = round(remaining_cost / new_quantity, 4)
    holding.quantity = new_quantity
