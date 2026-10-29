"""Opérations d'investissement : saisie, modification, suppression et rattachement des dividendes à un titre.

Toute écriture se termine par `rebuild_holdings` (positions dérivées) puis un seul `commit`.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.time import utcnow_naive
from app.domain.dividends import match_dividend_ticker
from app.domain.holdings import SELL_TYPES, is_trade
from app.integrations.currency import convert_amount
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.repositories import accounts as accounts_repo
from app.repositories import investment_transactions as repo
from app.repositories import portfolio as portfolio_repo
from app.schemas.investment import InvestmentTransactionCreate, InvestmentTransactionUpdate
from app.services.dividends import sync_reinvestment
from app.services.holdings.rebuild import rebuild_holdings
from app.services.holdings.replay import trade_cutoff

VALID_TYPES = {"versement", "retrait", "dividende", "achat", "vente", "frais"}
TRADE_FIELDS = {"type", "date", "ticker", "quantity", "unit_price", "price_currency", "fees"}
DIVIDEND_FIELDS = {"type", "date", "ticker", "quantity", "amount", "currency", "reinvested"}
TYPE_ERROR = "Investment transaction type must be one of: " + ", ".join(sorted(VALID_TYPES))


def _check_trade(db: Session, account_id: int, tx_type: str, date: datetime, ticker: str | None, quantity: float | None) -> None:
    """Un achat/une vente exige un titre et une quantité, et ne peut précéder l'inventaire Point Zéro."""
    if tx_type in {"achat", "vente"} and (not ticker or not quantity or quantity <= 0):
        raise BusinessRuleError("Un achat ou une vente exige un titre (ticker) et une quantité > 0")
    if not is_trade(tx_type, ticker, quantity):
        return
    cutoff = trade_cutoff(db, account_id, ticker)
    if cutoff and date <= cutoff:
        raise BusinessRuleError(
            f"Opération sur {ticker.upper()} antérieure au Point Zéro des positions ({cutoff:%d/%m/%Y %H:%M}) : "
            "elle est déjà couverte par l'inventaire, modifie plutôt l'inventaire du Point Zéro"
        )


def _check_dividend(db: Session, account_id: int, *, tx_type: str, date: datetime, ticker: str | None,
                    quantity: float | None, reinvested: bool, withholding_tax: float | None) -> None:
    """Retenue et réinvestissement n'existent que pour un dividende ; réinvestir exige titre + parts reçues."""
    if tx_type != "dividende":
        if reinvested or withholding_tax:
            raise BusinessRuleError("Retenue à la source et réinvestissement ne concernent que les dividendes")
        return
    if reinvested:
        if not ticker or not quantity or quantity <= 0:
            raise BusinessRuleError("Un dividende réinvesti exige un titre et le nombre de parts reçues")
        _check_trade(db, account_id, "achat", date, ticker, quantity)


def _check_zero_point(db: Session, account_id: int, day: datetime) -> None:
    active_zero_point = portfolio_repo.latest_zero_point(db, account_id)
    if active_zero_point and day < active_zero_point.date:
        raise BusinessRuleError("Transaction date cannot be before active zero point")


def _flag_distributing(db: Session, account_id: int, ticker: str | None) -> None:
    """Un dividende saisi sur une position la marque comme distribuante (si non renseigné)."""
    if not ticker:
        return
    holding = repo.holding(db, account_id, ticker)
    if holding is not None and holding.pays_dividends is None:
        holding.pays_dividends = True


def _derive_unit_price(tx: InvestmentTransaction) -> None:
    """Sans prix unitaire, on le déduit du montant (frais exclus) dans la devise de saisie."""
    if tx.unit_price or not is_trade(tx.type, tx.ticker, tx.quantity):
        return
    fees = tx.fees or 0.0
    gross = tx.original_amount + fees if tx.type in SELL_TYPES else tx.original_amount - fees
    if gross > 0:
        tx.unit_price = round(gross / tx.quantity, 6)
        tx.price_currency = tx.currency


async def _in_account_currency(db: Session, account: Account, amount: float, currency: str, day: datetime) -> float:
    if currency != account.currency:
        return await convert_amount(amount=amount, from_currency=currency, to_currency=account.currency, date=day.date(), db=db)
    return amount


async def _finish(db: Session, tx: InvestmentTransaction, *, sync_dividend: bool) -> InvestmentTransaction:
    """Achat lié du dividende, positions, marque « distribuant », puis commit (dans cet ordre)."""
    if sync_dividend:
        sync_reinvestment(db, tx)
    await rebuild_holdings(db, tx.account_id)
    if tx.type == "dividende":
        _flag_distributing(db, tx.account_id, tx.ticker)
    db.commit()
    db.refresh(tx)
    return tx


def list_transactions(db: Session, account_id: int | None, skip: int, limit: int | None) -> list[InvestmentTransaction]:
    return repo.list_for(db, account_id, skip, limit)


def link_dividends(db: Session, account_id: int, dry_run: bool) -> dict:
    """Rattache les dividendes sans titre d'un compte à une de ses positions, d'après leur libellé.

    `dry_run` se contente de proposer ; les libellés ambigus ou inconnus restent non rattachés.
    """
    if not accounts_repo.get(db, account_id):
        raise NotFoundError("Account not found")
    candidates = repo.dividend_link_candidates(db, account_id)
    matched, unmatched = [], []
    for tx in repo.unlinked_dividends(db, account_id):
        ticker = match_dividend_ticker(tx.note, list(candidates.items()))
        entry = {"id": tx.id, "date": tx.date.isoformat(), "note": tx.note, "amount": tx.amount, "currency": tx.currency}
        if ticker:
            matched.append({**entry, "ticker": ticker})
            if not dry_run:
                tx.ticker = ticker
        else:
            unmatched.append(entry)

    if not dry_run and matched:
        for ticker in {m["ticker"] for m in matched}:
            _flag_distributing(db, account_id, ticker)
        db.commit()
    return {"applied": not dry_run, "matched": matched, "unmatched": unmatched}


def _validate_new(db: Session, payload: InvestmentTransactionCreate) -> tuple[Account, str]:
    account = accounts_repo.get(db, payload.account_id)
    if not account:
        raise NotFoundError("Account not found")
    if account.type not in {"investissement", "assurance_vie"}:
        raise BusinessRuleError("Account must be of type investissement or assurance_vie")
    tx_type = payload.type.strip().lower()
    if tx_type not in VALID_TYPES:
        raise BusinessRuleError(TYPE_ERROR)
    _check_trade(db, payload.account_id, tx_type, payload.date, payload.ticker, payload.quantity)
    if tx_type == "dividende" and not payload.ticker:
        raise BusinessRuleError("Un dividende doit être rattaché à un titre (ticker)")
    _check_dividend(
        db, payload.account_id, tx_type=tx_type, date=payload.date, ticker=payload.ticker,
        quantity=payload.quantity, reinvested=payload.reinvested, withholding_tax=payload.withholding_tax,
    )
    _check_zero_point(db, payload.account_id, payload.date)
    return account, tx_type


async def create_transaction(db: Session, payload: InvestmentTransactionCreate) -> InvestmentTransaction:
    account, tx_type = _validate_new(db, payload)
    currency = payload.currency or account.currency
    tx = InvestmentTransaction(
        account_id=payload.account_id,
        date=payload.date,
        type=tx_type,
        amount=await _in_account_currency(db, account, payload.amount, currency, payload.date),
        currency=currency,
        original_amount=payload.amount,
        note=payload.note,
        asset_class=payload.asset_class,
        sector=payload.sector,
        geographic_zone=payload.geographic_zone,
        ticker=payload.ticker.upper().strip() if payload.ticker else None,
        isin=payload.isin.upper().strip() if payload.isin else None,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        price_currency=(payload.price_currency or (currency if payload.unit_price else None) or "").upper() or None,
        fees=payload.fees,
        withholding_tax=payload.withholding_tax,
        reinvested=payload.reinvested,
        etf_profile_id=payload.etf_profile_id,
    )
    _derive_unit_price(tx)
    repo.add(db, tx)
    account.last_verified_at = utcnow_naive()
    db.flush()
    return await _finish(db, tx, sync_dividend=tx_type == "dividende")


def _get_editable(db: Session, tx_id: int, reinvest_message: str) -> InvestmentTransaction:
    tx = repo.get(db, tx_id)
    if not tx:
        raise NotFoundError("Investment transaction not found")
    if tx.reinvest_of_id is not None:
        raise ConflictError(reinvest_message)
    return tx


async def delete_transaction(db: Session, tx_id: int) -> None:
    tx = _get_editable(db, tx_id, "Cet achat vient d'un dividende réinvesti : modifie ou supprime le dividende")
    account_id = tx.account_id
    repo.delete_reinvestments(db, tx.id)
    for linked in repo.linked_bank_transactions(db, tx.id):
        linked.linked_investment_transaction_id = None
        linked.is_transfer = False
    # Les FK des bases migrées n'ont pas de ON DELETE SET NULL : le lien doit être nul en base avant le DELETE
    db.flush()
    repo.delete(db, tx)
    db.flush()
    await rebuild_holdings(db, account_id)
    db.commit()


async def _normalize_update(db: Session, tx: InvestmentTransaction, account: Account, data: dict) -> datetime:
    """Valide et complète les champs modifiés (type, montant converti, contrôles). Renvoie la nouvelle date."""
    if "type" in data and data["type"] is not None:
        tx_type = data["type"].strip().lower()
        if tx_type not in VALID_TYPES:
            raise BusinessRuleError(TYPE_ERROR)
        data["type"] = tx_type
    new_date = data.get("date", tx.date)
    _check_zero_point(db, tx.account_id, new_date)

    # Montant, devise ou date modifiés : on reconvertit dans la devise du compte
    if "amount" in data or "currency" in data or "date" in data:
        original_amount = data.get("amount", tx.original_amount)
        currency = data.get("currency", tx.currency)
        data["amount"] = await _in_account_currency(db, account, original_amount, currency, data.get("date", tx.date))
        data["original_amount"] = original_amount
        data["currency"] = currency

    # Modifier la partie « titre » d'une opération couverte par le Point Zéro n'aurait aucun effet sur les
    # positions : on refuse, pour l'ancienne comme pour la nouvelle version (la note reste modifiable).
    if TRADE_FIELDS & data.keys():
        _check_trade(db, tx.account_id, tx.type, tx.date, tx.ticker, tx.quantity)
        _check_trade(db, tx.account_id, data.get("type", tx.type), new_date, data.get("ticker", tx.ticker), data.get("quantity", tx.quantity))

    new_type = data.get("type", tx.type)
    if new_type != "dividende":
        # Hors dividende, ces champs n'ont plus de sens : on les remet à zéro (l'achat lié sera supprimé)
        data["reinvested"], data["withholding_tax"] = False, None
    if DIVIDEND_FIELDS & data.keys():
        # Pas de contrôle sur une simple retouche de libellé (ex. dividende réinvesti antérieur à un nouveau Point Zéro)
        _check_dividend(
            db, tx.account_id, tx_type=new_type, date=new_date,
            ticker=data.get("ticker", tx.ticker), quantity=data.get("quantity", tx.quantity),
            reinvested=bool(data.get("reinvested", tx.reinvested)),
            withholding_tax=data.get("withholding_tax", tx.withholding_tax),
        )
    return new_date


async def update_transaction(db: Session, tx_id: int, payload: InvestmentTransactionUpdate) -> InvestmentTransaction:
    tx = _get_editable(db, tx_id, "Cet achat vient d'un dividende réinvesti : modifie le dividende")
    account = accounts_repo.get(db, tx.account_id)
    data = payload.model_dump(exclude_unset=True)
    await _normalize_update(db, tx, account, data)
    for key, value in data.items():
        setattr(tx, key, value)
    if tx.ticker:
        tx.ticker = tx.ticker.upper().strip()
    if tx.price_currency:
        tx.price_currency = tx.price_currency.upper()
    _derive_unit_price(tx)
    db.flush()
    return await _finish(db, tx, sync_dividend=bool(DIVIDEND_FIELDS & data.keys()))
