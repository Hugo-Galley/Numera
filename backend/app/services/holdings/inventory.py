"""Inventaire Point Zéro et positions d'un compte : lecture enrichie, saisie de l'inventaire, PRU estimés.

Quantité, PRU et devise ne s'écrivent jamais sur une position : on modifie l'inventaire, puis
`rebuild_holdings` recalcule les positions (`portfolio_holdings` est dérivé).
"""
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.time import utcnow_naive
from app.domain.holdings import normalize_ticker
from app.models.account import Account
from app.models.holding_baseline_item import HoldingBaselineItem
from app.repositories import accounts as accounts_repo
from app.repositories import holdings as repo
from app.schemas.holding import (
    ApplyCostsRequest,
    BaselineInventoryRequest,
    CostEstimateRead,
    PortfolioHoldingCreate,
    PortfolioHoldingRead,
    PortfolioHoldingUpdate,
)
from app.services.holdings.cost_estimates import estimate_baseline_costs
from app.services.holdings.enrich import enrich_all
from app.services.holdings.rebuild import rebuild_holdings
from app.services.holdings.replay import trade_cutoff
from app.services.market.suggestions import suggest_holdings_from_notes


def _get_account(db: Session, account_id: int) -> Account:
    account = accounts_repo.get(db, account_id)
    if not account:
        raise NotFoundError("Account not found")
    return account


def _baseline_item(account_id: int, ticker: str, baseline_date, line) -> HoldingBaselineItem:
    return HoldingBaselineItem(
        account_id=account_id,
        baseline_date=baseline_date,
        ticker=ticker,
        isin=line.isin.upper().strip() if line.isin else None,
        asset_name=line.asset_name.strip(),
        quantity=line.quantity,
        buy_price_avg=line.buy_price_avg or None,
        currency=line.currency.upper(),
        etf_profile_id=line.etf_profile_id,
    )


async def list_holdings(db: Session, account_id: int | None) -> list[PortfolioHoldingRead]:
    return await enrich_all(db, repo.list_all(db, account_id))


async def suggestions(db: Session, account_id: int) -> list[dict]:
    """Titres suggérés pour l'inventaire Point Zéro d'après les libellés des anciennes opérations."""
    _get_account(db, account_id)
    return await suggest_holdings_from_notes(db, account_id)


async def cost_estimates(db: Session, account_id: int) -> list[CostEstimateRead]:
    _get_account(db, account_id)
    return [
        CostEstimateRead(
            ticker=e.ticker, asset_name=e.asset_name, quantity=e.quantity, currency=e.currency,
            current_cost=e.current_cost, estimate=e.estimate, buys=e.buys,
            bought_quantity=round(e.bought_quantity, 6), sold_quantity=round(e.sold_quantity, 6),
            coverage=round(e.coverage, 4) if e.coverage is not None else None,
            first_buy=e.first_buy.isoformat() if e.first_buy else None,
            method=e.method, amount_only_buys=e.amount_only_buys,
        )
        for e in await estimate_baseline_costs(db, account_id)
    ]


async def _rebuild_and_list(db: Session, account_id: int) -> list[PortfolioHoldingRead]:
    db.flush()
    await rebuild_holdings(db, account_id)
    db.commit()
    return await enrich_all(db, repo.list_all(db, account_id))


async def apply_costs(db: Session, payload: ApplyCostsRequest) -> list[PortfolioHoldingRead]:
    """Enregistre les PRU validés dans l'inventaire Point Zéro, puis recalcule les positions."""
    _get_account(db, payload.account_id)
    items = {i.ticker: i for i in repo.baseline_items(db, payload.account_id)}
    for line in payload.items:
        item = items.get(normalize_ticker(line.ticker))
        if item is None:
            raise BusinessRuleError(f"{line.ticker} n'est pas dans l'inventaire du Point Zéro")
        item.buy_price_avg = line.buy_price_avg
    return await _rebuild_and_list(db, payload.account_id)


async def set_baseline(db: Session, payload: BaselineInventoryRequest) -> list[PortfolioHoldingRead]:
    """Remplace l'inventaire Point Zéro, daté de `payload.date` (maintenant par défaut)."""
    account = _get_account(db, payload.account_id)
    baseline_date = payload.date or utcnow_naive()
    repo.delete_baseline(db, payload.account_id)
    account.holdings_baseline_date = baseline_date

    by_ticker: dict[str, HoldingBaselineItem] = {}
    for item in payload.holdings:
        if item.quantity <= 0:
            continue
        ticker = normalize_ticker(item.ticker)
        by_ticker[ticker] = _baseline_item(payload.account_id, ticker, baseline_date, item)
    repo.add_baseline_items(db, list(by_ticker.values()))
    return await _rebuild_and_list(db, payload.account_id)


async def create_holding(db: Session, payload: PortfolioHoldingCreate) -> PortfolioHoldingRead:
    """Ajoute une ligne à l'inventaire Point Zéro du compte, datée de maintenant."""
    _get_account(db, payload.account_id)
    ticker = normalize_ticker(payload.ticker)
    repo.delete_baseline(db, payload.account_id, ticker)
    repo.add_baseline_items(db, [_baseline_item(payload.account_id, ticker, utcnow_naive(), payload)])
    db.flush()
    await rebuild_holdings(db, payload.account_id)
    db.commit()

    holding = repo.holding(db, payload.account_id, ticker)
    if holding is None:
        raise BusinessRuleError("Position nulle : rien à ajouter")
    return (await enrich_all(db, [holding]))[0]


async def update_holding(db: Session, holding_id: int, payload: PortfolioHoldingUpdate) -> PortfolioHoldingRead:
    """Métadonnées modifiées directement ; quantité, PRU, devise via la ligne d'inventaire du titre."""
    holding = repo.get(db, holding_id)
    if not holding:
        raise NotFoundError("Holding not found")
    if payload.ticker is not None and normalize_ticker(payload.ticker) != holding.ticker:
        raise BusinessRuleError("Le ticker d'une position ne peut pas être modifié")

    item = repo.baseline_item(db, holding.account_id, holding.ticker)
    if payload.isin is not None:
        holding.isin = payload.isin.upper().strip() if payload.isin else None
    if payload.asset_name is not None:
        holding.asset_name = payload.asset_name.strip()
    if payload.etf_profile_id is not None:
        holding.etf_profile_id = payload.etf_profile_id
    if "pays_dividends" in payload.model_fields_set:
        holding.pays_dividends = payload.pays_dividends
    if item is not None:
        item.isin, item.asset_name, item.etf_profile_id = holding.isin, holding.asset_name, holding.etf_profile_id

    if {"quantity", "buy_price_avg", "currency"} & payload.model_fields_set:
        if item is None:
            raise BusinessRuleError(
                "Cette position provient uniquement d'opérations : modifie les opérations, ou refais l'inventaire du Point Zéro"
            )
        if payload.quantity is not None:
            item.quantity = payload.quantity
        if "buy_price_avg" in payload.model_fields_set:
            item.buy_price_avg = payload.buy_price_avg or None
        if payload.currency is not None:
            item.currency = payload.currency.upper()
        db.flush()
        await rebuild_holdings(db, holding.account_id)

    db.commit()
    holding = repo.get(db, holding_id)
    if holding is None:
        raise BusinessRuleError("La position est désormais nulle")
    return (await enrich_all(db, [holding]))[0]


async def delete_holding(db: Session, holding_id: int) -> None:
    """Retire le titre de l'inventaire Point Zéro (refusé s'il reste des opérations sur ce titre)."""
    holding = repo.get(db, holding_id)
    if not holding:
        raise NotFoundError("Holding not found")
    cutoff = trade_cutoff(db, holding.account_id, holding.ticker)
    if repo.later_trade_exists(db, holding.account_id, holding.ticker, cutoff):
        raise ConflictError("Des opérations portent sur ce titre après le Point Zéro : supprime-les ou enregistre une vente")
    account_id = holding.account_id
    repo.delete_baseline(db, account_id, holding.ticker)
    db.flush()
    await rebuild_holdings(db, account_id)
    db.commit()
