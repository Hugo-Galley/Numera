"""Dividendes d'investissement : achat lié d'un dividende réinvesti, dividendes convertis en EUR.

Règles et agrégats purs : `domain/dividends.py`.
"""
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.dividends import DividendRow
from app.integrations.currency import CurrencyConversionError, convert_amount
from app.models.investment_transaction import InvestmentTransaction
from app.repositories import investment_transactions as repo

logger = get_logger(__name__)


def sync_reinvestment(db: Session, dividend: InvestmentTransaction) -> None:
    """Recrée l'achat lié d'un dividende réinvesti (ou le supprime s'il ne l'est plus). Ne commit pas.

    Le dividende doit déjà avoir un `id` (flush). `quantity` = parts reçues en échange du net.
    """
    repo.delete_reinvestments(db, dividend.id)
    if not dividend.reinvested:
        return
    repo.add(
        db,
        InvestmentTransaction(
            account_id=dividend.account_id,
            date=dividend.date,
            type="achat",
            amount=dividend.amount,
            currency=dividend.currency,
            original_amount=dividend.original_amount,
            note=dividend.note,
            asset_class=dividend.asset_class,
            sector=dividend.sector,
            geographic_zone=dividend.geographic_zone,
            ticker=dividend.ticker,
            isin=dividend.isin,
            quantity=dividend.quantity,
            unit_price=round(dividend.original_amount / dividend.quantity, 6),
            price_currency=dividend.currency,
            etf_profile_id=dividend.etf_profile_id,
            reinvest_of_id=dividend.id,
        ),
    )


async def load_dividends_eur(db: Session, account_id: int | None = None) -> list[DividendRow]:
    """
    Tous les dividendes (optionnellement d'un compte) en EUR.

    Le net vient de `amount`, déjà converti dans la devise du compte à la saisie (aucun appel de taux
    pour un compte en EUR) ; la retenue, exprimée dans `currency`, est convertie au taux du jour de versement.
    """
    account_currency = repo.account_currencies(db)

    rows: list[DividendRow] = []
    for tx in repo.dividends(db, account_id):
        try:
            net = await convert_amount(
                tx.amount, account_currency.get(tx.account_id, "EUR"), "EUR", date=tx.date.date(), db=db
            )
            tax = (
                await convert_amount(tx.withholding_tax, tx.currency, "EUR", date=tx.date.date(), db=db)
                if tx.withholding_tax
                else 0.0
            )
        except CurrencyConversionError as exc:
            logger.warning(f"Dividend {tx.id} skipped (no exchange rate): {exc}")
            continue
        rows.append(DividendRow(tx=tx, net_eur=net, tax_eur=tax))
    return rows
