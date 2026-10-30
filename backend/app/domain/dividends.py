"""Dividendes : rattachement d'un libellé à un titre, lignes en EUR et agrégats par position (sans base).

Un dividende est une `investment_transaction` de type `dividende` :
- `amount` = net reçu (devise du compte), `original_amount` / `currency` = saisie d'origine ;
- `withholding_tax` = retenue à la source, dans `currency` (brut = net + retenue) ;
- `ticker` = titre qui l'a versé ;
- `reinvested` = True : un `achat` lié (`reinvest_of_id`) augmente la position.
"""
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime, timedelta

from app.domain.market import extract_asset_clean_name
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.schemas.dividend import DividendTicker, DividendTotals, DividendUnlinked

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


def month_keys(end: datetime, months: int) -> list[str]:
    """Les `months` derniers mois (« AAAA-MM ») jusqu'au mois de `end` inclus, du plus ancien au plus récent."""
    keys, year, month = [], end.year, end.month
    for _ in range(months):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(keys))


@dataclass
class DividendAggregates:
    totals: DividendTotals = field(default_factory=DividendTotals)
    unlinked: DividendUnlinked = field(default_factory=DividendUnlinked)
    by_month: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    by_year: dict[int, dict] = field(default_factory=lambda: defaultdict(lambda: {"count": 0, "net": 0.0, "tax": 0.0}))
    by_ticker: dict[str, dict] = field(default_factory=dict)


def aggregate_dividends(rows: list[DividendRow], since: datetime) -> DividendAggregates:
    """Totaux, par mois, par année, par titre (12 derniers mois depuis `since`) et dividendes non rattachés."""
    agg = DividendAggregates()
    for row in rows:
        tx = row.tx
        agg.totals.count += 1
        agg.totals.net_eur += row.net_eur
        agg.totals.withholding_eur += row.tax_eur
        if tx.date >= since:
            agg.totals.last_12m_eur += row.net_eur
        agg.by_month[tx.date.strftime("%Y-%m")] += row.net_eur
        year = agg.by_year[tx.date.year]
        year["count"] += 1
        year["net"] += row.net_eur
        year["tax"] += row.tax_eur

        if not tx.ticker:
            agg.unlinked.count += 1
            agg.unlinked.total_eur += row.net_eur
            continue
        item = agg.by_ticker.setdefault(
            tx.ticker.upper(), {"count": 0, "total": 0.0, "last12": 0.0, "last_date": None, "name": tx.note or tx.ticker}
        )
        item["count"] += 1
        item["total"] += row.net_eur
        if tx.date >= since:
            item["last12"] += row.net_eur
        if item["last_date"] is None or tx.date > item["last_date"]:
            item["last_date"] = tx.date
    return agg


def position_values(holdings: list[PortfolioHolding], quotes: dict) -> dict[str, dict]:
    """Coût de revient et valeur actuelle (EUR) par ticker, pour les rendements ; incomplets si un coût ou un cours manque."""
    positions: dict[str, dict] = {}
    for h in holdings:
        pos = positions.setdefault(h.ticker.upper(), {"name": h.asset_name, "cost": 0.0, "has_cost": True, "value": 0.0, "has_value": True})
        if h.cost_basis_eur:
            pos["cost"] += h.cost_basis_eur
        else:
            pos["has_cost"] = False
        price_eur = (quotes.get(h.ticker.upper()) or {}).get("price_eur") or 0.0
        if price_eur > 0:
            pos["value"] += h.quantity * price_eur
        else:
            pos["has_value"] = False
    return positions


def dividend_tickers(by_ticker: dict[str, dict], positions: dict[str, dict]) -> list[DividendTicker]:
    """Dividendes par titre avec rendement sur coût et rendement courant, par total décroissant."""
    tickers: list[DividendTicker] = []
    for ticker, item in by_ticker.items():
        pos = positions.get(ticker)
        tickers.append(
            DividendTicker(
                ticker=ticker,
                asset_name=pos["name"] if pos else item["name"],
                count=item["count"],
                total_eur=round(item["total"], 2),
                last_12m_eur=round(item["last12"], 2),
                last_date=item["last_date"].date().isoformat() if item["last_date"] else None,
                yield_on_cost_pct=round(item["last12"] / pos["cost"] * 100, 2) if pos and pos["has_cost"] and pos["cost"] > 0 else None,
                current_yield_pct=round(item["last12"] / pos["value"] * 100, 2) if pos and pos["has_value"] and pos["value"] > 0 else None,
            )
        )
    tickers.sort(key=lambda t: t.total_eur, reverse=True)
    return tickers
