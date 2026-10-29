"""Reconstruction des positions (`portfolio_holdings`) d'un compte depuis l'inventaire et les opérations."""
from sqlalchemy.orm import Session

from app.domain.holdings import EPSILON
from app.models.portfolio_holding import PortfolioHolding
from app.repositories.investissement import holdings as repo
from app.services.investissement.holdings.replay import replay_account


async def rebuild_holdings(db: Session, account_id: int) -> None:
    """Recalcule toutes les positions du compte depuis l'inventaire et les opérations. Ne commit pas."""
    positions = (await replay_account(db, account_id)).positions
    existing = repo.holdings_by_ticker(db, account_id)
    for ticker, holding in existing.items():
        pos = positions.get(ticker)
        if pos is None or pos.quantity <= EPSILON:
            repo.delete_holding(db, holding)

    for ticker, pos in positions.items():
        if pos.quantity <= EPSILON:
            continue
        pru = round(pos.cost / pos.quantity, 4) if pos.cost else None
        cost_eur = round(pos.cost_eur, 2) if pos.cost_eur else None
        holding = existing.get(ticker)
        if holding is None:
            repo.add_holding(
                db,
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
                ),
            )
        else:
            holding.quantity = pos.quantity
            holding.buy_price_avg = pru
            holding.currency = pos.currency
            holding.cost_basis_eur = cost_eur
            holding.isin = holding.isin or pos.isin
            holding.etf_profile_id = holding.etf_profile_id or pos.etf_profile_id
    db.flush()
