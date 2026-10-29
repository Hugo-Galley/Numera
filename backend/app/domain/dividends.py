"""Dividendes : rattachement d'un libellé à un titre, lignes en EUR et agrégats par position (sans base).

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

from app.domain.market import extract_asset_clean_name
from app.models.investment_transaction import InvestmentTransaction

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


@dataclass
class DividendRow:
    tx: InvestmentTransaction
    net_eur: float
    tax_eur: float

    @property
    def gross_eur(self) -> float:
        return self.net_eur + self.tax_eur


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
