"""Revenus et coûts d'un compte titres : plus-values réalisées, dividendes et frais, en EUR."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.domain.holdings import Replay, is_trade
from app.repositories.investissement import investment_transactions as tx_repo
from app.services.investissement.dividends import load_dividends_eur
from app.services.investissement.portfolio.books import FxBook


def realized_summary(replay: Replay) -> tuple[dict[int, dict], float, int]:
    """Plus-values réalisées par année, total et nombre de ventes au coût inconnu."""
    realized_by_year: dict[int, dict] = {}
    realized_total = 0.0
    realized_unknown = 0
    for sale in replay.realized:
        entry = realized_by_year.setdefault(sale.date.year, {"year": sale.date.year, "realized_eur": 0.0, "proceeds_eur": 0.0, "sales": 0})
        entry["sales"] += 1
        if sale.realized_eur is None:
            realized_unknown += 1
            continue
        entry["realized_eur"] += sale.realized_eur
        entry["proceeds_eur"] += sale.proceeds_eur or 0.0
        realized_total += sale.realized_eur
    return realized_by_year, realized_total, realized_unknown


async def dividend_totals(db: Session, account_id: int, today: datetime) -> tuple[float, float, float]:
    """Dividendes nets (total, 12 derniers mois) et retenues à la source."""
    dividend_rows = await load_dividends_eur(db, account_id)
    since = today - timedelta(days=365)
    dividends_net = sum(r.net_eur for r in dividend_rows)
    dividends_12m = sum(r.net_eur for r in dividend_rows if r.tx.date >= since)
    dividends_tax = sum(r.tax_eur for r in dividend_rows)
    return dividends_net, dividends_12m, dividends_tax


async def fees_eur(db: Session, account_id: int, baseline_date: datetime | None, currency: str, fx: FxBook) -> float:
    """Frais postérieurs au Point Zéro : opérations `frais` et frais de courtage des achats/ventes."""
    total = 0.0
    for tx in tx_repo.for_account(db, account_id):
        if baseline_date is not None and tx.date <= baseline_date:
            continue
        if tx.type == "frais":
            converted = await fx.convert(tx.amount, currency, "EUR", tx.date.date())
        elif tx.fees and tx.type in ("achat", "vente", "versement", "retrait") and is_trade(tx.type, tx.ticker, tx.quantity):
            converted = await fx.convert(tx.fees, (tx.price_currency or tx.currency or "EUR").upper(), "EUR", tx.date.date())
        else:
            continue
        total += converted or 0.0
    return total
