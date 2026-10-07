from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.account import Account
from app.models.portfolio_holding import PortfolioHolding
from app.models.etf_profile import EtfProfile
from app.models.holding_baseline_item import HoldingBaselineItem
from app.models.investment_transaction import InvestmentTransaction
from app.schemas.holding import (
    PortfolioHoldingCreate,
    PortfolioHoldingRead,
    PortfolioHoldingUpdate,
    BaselineInventoryRequest,
)
from app.core.currency import get_exchange_rates
from app.core.dividends import HoldingDividends, load_dividends_eur, summarize_by_holding
from app.core.holdings import TRADE_TYPES, normalize_ticker, rebuild_holdings, trade_cutoff
from app.core.market_data import get_market_quotes, suggest_holdings_from_notes
from app.core.time import utcnow_naive

router = APIRouter(prefix="/holdings", tags=["holdings"])


async def _enrich_holding_with_quote(
    holding: PortfolioHolding, quotes: dict, rates: dict | None = None, divs: HoldingDividends | None = None
) -> PortfolioHoldingRead:
    sym = holding.ticker.upper().strip()
    quote = quotes.get(sym, {})
    price = quote.get("price", 0.0) or 0.0
    price_eur = quote.get("price_eur", 0.0) or 0.0
    if rates is None:
        rates = await get_exchange_rates("EUR")

    curr_val_eur = holding.quantity * price_eur if price_eur > 0 else 0.0
    # Coût de revient en EUR : aux taux historiques des achats si connu, sinon PRU converti au taux du jour
    tot_invested_eur = holding.cost_basis_eur
    if tot_invested_eur is None and holding.buy_price_avg and holding.buy_price_avg > 0:
        fx = rates.get((holding.currency or "EUR").upper())
        if fx:
            tot_invested_eur = holding.quantity * holding.buy_price_avg / fx

    gain_eur = None
    gain_pct = None
    if tot_invested_eur is not None and tot_invested_eur > 0 and curr_val_eur > 0:
        gain_eur = round(curr_val_eur - tot_invested_eur, 2)
        gain_pct = round((gain_eur / tot_invested_eur) * 100.0, 2)

    divs = divs or HoldingDividends()
    total_return_eur = total_return_pct = None
    if gain_eur is not None:
        total_return_eur = round(gain_eur + divs.total_eur, 2)
        total_return_pct = round(total_return_eur / tot_invested_eur * 100.0, 2)

    return PortfolioHoldingRead(
        id=holding.id,
        account_id=holding.account_id,
        ticker=holding.ticker,
        isin=holding.isin,
        asset_name=holding.asset_name,
        quantity=holding.quantity,
        buy_price_avg=holding.buy_price_avg,
        currency=holding.currency,
        etf_profile_id=holding.etf_profile_id,
        created_at=holding.created_at,
        updated_at=holding.updated_at,
        current_price=round(price, 4) if price > 0 else None,
        current_price_eur=round(price_eur, 4) if price_eur > 0 else None,
        quote_currency=quote.get("currency") if price > 0 else None,
        price_date=quote.get("price_date") if price > 0 else None,
        price_stale=bool(quote.get("stale", price <= 0)),
        current_value_eur=round(curr_val_eur, 2) if curr_val_eur > 0 else None,
        total_invested_eur=round(tot_invested_eur, 2) if tot_invested_eur is not None else None,
        gain_eur=gain_eur,
        gain_pct=gain_pct,
        is_etf=bool(holding.etf_profile_id or quote.get("type") == "ETF"),
        pays_dividends=holding.pays_dividends,
        dividends_received_eur=round(divs.total_eur, 2),
        dividends_12m_eur=round(divs.last_12m_eur, 2),
        last_dividend_date=divs.last_date.isoformat() if divs.last_date else None,
        total_return_eur=total_return_eur,
        total_return_pct=total_return_pct,
    )


async def _enrich_all(db: Session, holdings: list[PortfolioHolding]) -> list[PortfolioHoldingRead]:
    quotes = await get_market_quotes([h.ticker for h in holdings], db=db)
    rates = await get_exchange_rates("EUR")
    dividends = summarize_by_holding(await load_dividends_eur(db))
    return [
        await _enrich_holding_with_quote(h, quotes, rates, dividends.get((h.account_id, h.ticker.upper())))
        for h in holdings
    ]


def _account_holdings(db: Session, account_id: int) -> list[PortfolioHolding]:
    return (
        db.query(PortfolioHolding)
        .filter(PortfolioHolding.account_id == account_id)
        .order_by(PortfolioHolding.id.asc())
        .all()
    )


def _get_account(db: Session, account_id: int) -> Account:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("", response_model=List[PortfolioHoldingRead])
async def list_holdings(
    account_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(PortfolioHolding)
    if account_id is not None:
        query = query.filter(PortfolioHolding.account_id == account_id)
    holdings = query.order_by(PortfolioHolding.id.asc()).all()
    return await _enrich_all(db, holdings)


@router.get("/suggestions")
async def get_holding_suggestions(
    account_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """
    Suggests holdings for the Point Zéro baseline by analyzing historical transaction notes.
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return await suggest_holdings_from_notes(db, account_id)


@router.post("/baseline", response_model=List[PortfolioHoldingRead])
async def set_baseline_inventory(
    payload: BaselineInventoryRequest,
    db: Session = Depends(get_db),
):
    """
    Point Zéro / état des lieux des positions d'un compte, à une date donnée (maintenant par défaut).
    Remplace l'inventaire ; les opérations sur titres postérieures à cette date sont rejouées par-dessus.
    """
    account = _get_account(db, payload.account_id)
    baseline_date = payload.date or utcnow_naive()

    db.query(HoldingBaselineItem).filter(HoldingBaselineItem.account_id == payload.account_id).delete()
    account.holdings_baseline_date = baseline_date

    by_ticker: dict[str, HoldingBaselineItem] = {}
    for item in payload.holdings:
        if item.quantity <= 0:
            continue
        ticker = normalize_ticker(item.ticker)
        by_ticker[ticker] = HoldingBaselineItem(
            account_id=payload.account_id,
            baseline_date=baseline_date,
            ticker=ticker,
            isin=item.isin.upper().strip() if item.isin else None,
            asset_name=item.asset_name.strip(),
            quantity=item.quantity,
            buy_price_avg=item.buy_price_avg or None,
            currency=item.currency.upper(),
            etf_profile_id=item.etf_profile_id,
        )
    db.add_all(by_ticker.values())
    db.flush()

    await rebuild_holdings(db, payload.account_id)
    db.commit()
    return await _enrich_all(db, _account_holdings(db, payload.account_id))


@router.post("", response_model=PortfolioHoldingRead, status_code=201)
async def create_holding(
    payload: PortfolioHoldingCreate,
    db: Session = Depends(get_db),
):
    """Ajoute une ligne à l'inventaire Point Zéro du compte, datée de maintenant."""
    _get_account(db, payload.account_id)
    ticker = normalize_ticker(payload.ticker)
    db.query(HoldingBaselineItem).filter(
        HoldingBaselineItem.account_id == payload.account_id, HoldingBaselineItem.ticker == ticker
    ).delete()
    db.add(
        HoldingBaselineItem(
            account_id=payload.account_id,
            baseline_date=utcnow_naive(),
            ticker=ticker,
            isin=payload.isin.upper().strip() if payload.isin else None,
            asset_name=payload.asset_name.strip(),
            quantity=payload.quantity,
            buy_price_avg=payload.buy_price_avg or None,
            currency=payload.currency.upper(),
            etf_profile_id=payload.etf_profile_id,
        )
    )
    db.flush()
    await rebuild_holdings(db, payload.account_id)
    db.commit()

    holding = db.query(PortfolioHolding).filter(
        PortfolioHolding.account_id == payload.account_id, PortfolioHolding.ticker == ticker
    ).first()
    if holding is None:
        raise HTTPException(status_code=422, detail="Position nulle : rien à ajouter")
    return (await _enrich_all(db, [holding]))[0]


@router.put("/{holding_id}", response_model=PortfolioHoldingRead)
async def update_holding(
    holding_id: int,
    payload: PortfolioHoldingUpdate,
    db: Session = Depends(get_db),
):
    """
    Métadonnées (nom, ISIN, profil ETF) : modifiées directement.
    Quantité, PRU, devise : modifient la ligne d'inventaire Point Zéro du titre, puis les positions sont
    recalculées (impossible pour une position qui ne vient que d'opérations : modifier les opérations).
    """
    holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    if payload.ticker is not None and normalize_ticker(payload.ticker) != holding.ticker:
        raise HTTPException(status_code=422, detail="Le ticker d'une position ne peut pas être modifié")

    item = db.query(HoldingBaselineItem).filter(
        HoldingBaselineItem.account_id == holding.account_id, HoldingBaselineItem.ticker == holding.ticker
    ).first()

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

    position_fields = {"quantity", "buy_price_avg", "currency"} & payload.model_fields_set
    if position_fields:
        if item is None:
            raise HTTPException(
                status_code=422,
                detail="Cette position provient uniquement d'opérations : modifie les opérations, ou refais l'inventaire du Point Zéro",
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
    holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if holding is None:
        raise HTTPException(status_code=422, detail="La position est désormais nulle")
    return (await _enrich_all(db, [holding]))[0]


@router.delete("/{holding_id}", status_code=204)
async def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    """Retire le titre de l'inventaire Point Zéro (refusé s'il reste des opérations sur ce titre)."""
    holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    cutoff = trade_cutoff(db, holding.account_id, holding.ticker)
    later_trade = db.query(InvestmentTransaction.id).filter(
        InvestmentTransaction.account_id == holding.account_id,
        InvestmentTransaction.ticker == holding.ticker,
        InvestmentTransaction.quantity > 0,
        InvestmentTransaction.type.in_(TRADE_TYPES),
        *([InvestmentTransaction.date > cutoff] if cutoff else []),
    ).first()
    if later_trade is not None:
        raise HTTPException(
            status_code=409,
            detail="Des opérations portent sur ce titre après le Point Zéro : supprime-les ou enregistre une vente",
        )
    account_id = holding.account_id
    db.query(HoldingBaselineItem).filter(
        HoldingBaselineItem.account_id == account_id, HoldingBaselineItem.ticker == holding.ticker
    ).delete()
    db.flush()
    await rebuild_holdings(db, account_id)
    db.commit()
