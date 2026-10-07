"""Dividendes d'investissement : rattachement à un titre, réinvestissement, agrégats en EUR.

Un dividende est une `investment_transaction` de type `dividende` :
- `amount` = net reçu (devise du compte), `original_amount` / `currency` = saisie d'origine ;
- `withholding_tax` = retenue à la source, dans `currency` (brut = net + retenue) ;
- `ticker` = titre qui l'a versé ;
- `reinvested` = True : un `achat` lié (`reinvest_of_id`) augmente la position.
"""
import re
import unicodedata
from dataclasses import dataclass
from datetime import date as date_type, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.currency import CurrencyConversionError, convert_amount
from app.core.logging import get_logger
from app.core.market_data import extract_asset_clean_name
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction

logger = get_logger(__name__)

DIVIDEND_TYPE = "dividende"


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", ascii_text.lower()).strip()


# Noms usuels de cryptos → symbole (un libellé « Bitcoin » ou « Achat BTC » doit retrouver BTC-EUR)
CRYPTO_ALIASES = {
    "bitcoin": "btc", "ethereum": "eth", "ether": "eth", "solana": "sol", "ripple": "xrp", "cardano": "ada",
    "dogecoin": "doge", "litecoin": "ltc", "polkadot": "dot", "chainlink": "link", "avalanche": "avax",
}


def match_dividend_ticker(note: str | None, candidates: list[tuple[str, str]]) -> str | None:
    """Ticker dont le nom ou le symbole correspond au libellé du dividende (« Dividende Apple » → AAPL).

    `candidates` : couples (ticker, nom du titre). Renvoie None si aucun titre ou plusieurs titres
    correspondent (on ne devine pas).
    """
    name = extract_asset_clean_name(note or "")
    if not name:
        return None
    wanted = _norm(name)
    if not wanted:
        return None
    wanted_symbol = CRYPTO_ALIASES.get(wanted, wanted)

    matches: set[str] = set()
    for ticker, asset_name in candidates:
        symbol = _norm(ticker)
        base_symbol = _norm(re.split(r"[.\-]", ticker)[0])  # CW8.PA → cw8, BTC-EUR → btc
        label = _norm(asset_name)
        if wanted in (symbol, base_symbol) or wanted_symbol == base_symbol:
            matches.add(ticker)
        elif len(wanted) >= 4 and (label.startswith(wanted) or f" {wanted}" in f" {label}"):
            matches.add(ticker)
    return next(iter(matches)) if len(matches) == 1 else None


def sync_reinvestment(db: Session, dividend: InvestmentTransaction) -> None:
    """Recrée l'achat lié d'un dividende réinvesti (ou le supprime s'il ne l'est plus). Ne commit pas.

    Le dividende doit déjà avoir un `id` (flush). `quantity` = parts reçues en échange du net.
    """
    db.query(InvestmentTransaction).filter(InvestmentTransaction.reinvest_of_id == dividend.id).delete()
    db.flush()
    if not dividend.reinvested:
        return
    db.add(
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
        )
    )
    db.flush()


@dataclass
class DividendRow:
    tx: InvestmentTransaction
    net_eur: float
    tax_eur: float

    @property
    def gross_eur(self) -> float:
        return self.net_eur + self.tax_eur


async def load_dividends_eur(db: Session, account_id: int | None = None) -> list[DividendRow]:
    """
    Tous les dividendes (optionnellement d'un compte) en EUR.

    Le net vient de `amount`, déjà converti dans la devise du compte à la saisie (aucun appel de taux
    pour un compte en EUR) ; la retenue, exprimée dans `currency`, est convertie au taux du jour de versement.
    """
    query = db.query(InvestmentTransaction).filter(InvestmentTransaction.type == DIVIDEND_TYPE)
    if account_id is not None:
        query = query.filter(InvestmentTransaction.account_id == account_id)
    account_currency = {acc_id: cur for acc_id, cur in db.query(Account.id, Account.currency).all()}

    rows: list[DividendRow] = []
    for tx in query.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc()).all():
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


@dataclass
class HoldingDividends:
    total_eur: float = 0.0
    last_12m_eur: float = 0.0
    last_date: date_type | None = None
    count: int = 0


def summarize_by_holding(rows: list[DividendRow], today: datetime | None = None) -> dict[tuple[int, str], HoldingDividends]:
    """Dividendes nets par (compte, ticker) : total, 12 derniers mois, dernière date."""
    since = (today or datetime.now()) - timedelta(days=365)
    out: dict[tuple[int, str], HoldingDividends] = {}
    for row in rows:
        if not row.tx.ticker:
            continue
        item = out.setdefault((row.tx.account_id, row.tx.ticker.upper()), HoldingDividends())
        item.total_eur += row.net_eur
        item.count += 1
        if row.tx.date >= since:
            item.last_12m_eur += row.net_eur
        if item.last_date is None or row.tx.date.date() > item.last_date:
            item.last_date = row.tx.date.date()
    return out
