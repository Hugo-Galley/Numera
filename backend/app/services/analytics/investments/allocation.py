"""Répartitions : par compte d'investissement, par classe d'actifs / secteur / zone, patrimoine global, suggestions."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.holdings import replay_account
from app.core.portfolio import compute_portfolio, uses_positions
from app.domain.investments import AllocationGroups, patrimoine_items
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.repositories.analytics import investments as repo
from app.services.analytics.investments.flows import calculate_investment_flows
from app.services.wealth import account_values, active_accounts

DEFAULT_CLASSES = ["Actions", "Obligations", "Immobilier", "Liquidités", "Crypto", "Or & Matières Premières", "Private Equity"]
DEFAULT_SECTORS = ["Tech", "Santé", "Finance", "Energie", "Industrie", "Consommation", "Télécoms", "Luxe", "SaaS", "E-commerce", "Tourisme"]
DEFAULT_ZONES = ["Europe", "USA", "Asie", "Marchés Émergents", "France", "Monde", "Chine", "Japon"]


async def compute_allocation(db: Session, account_id: int | None = None) -> dict:
    accounts = repo.investment_accounts(db, account_id)
    now = datetime.now()
    values = await account_values(db, accounts)
    total_value = total_invested = 0.0
    items = []
    for acc in accounts:
        if uses_positions(acc, await replay_account(db, acc.id)):
            p = await compute_portfolio(db, acc, history=False)
            net_invested_eur, value_eur, source = p["net_invested_eur"], p["value_eur"], "positions"
        else:
            # Capital net investi aux taux historiques ; valeur identique au patrimoine (relevé, sinon solde),
            # 0 sans valorisation, jamais le capital investi
            flows = await calculate_investment_flows(db, acc, now, target_currency="EUR")
            net_invested_eur, value_eur, source = flows["net_invested_target"], values[acc.id].value_eur, values[acc.id].source
        total_invested += net_invested_eur
        total_value += value_eur
        items.append({
            "account_id": acc.id,
            "account_name": acc.name,
            "current_value": round(value_eur, 2),
            "net_invested": round(net_invested_eur, 2),
            "gain_eur": round(value_eur - net_invested_eur, 2),
            "currency": acc.currency,
            "value_source": source,
        })

    for item in items:
        item["percentage"] = round((item["current_value"] / total_value * 100.0), 2) if total_value > 0 else 0.0
        # Rendement du compte ; sans capital net investi positif, un pourcentage n'a pas de sens
        item["performance_pct"] = (
            round(item["gain_eur"] / item["net_invested"] * 100.0, 2) if item["net_invested"] > 0 else None
        )
    total_gain = total_value - total_invested
    total_perf_pct = (total_gain / total_invested * 100.0) if total_invested > 0 else 0.0
    items.sort(key=lambda i: i["current_value"], reverse=True)
    return {
        "total_current_value": round(total_value, 2),
        "total_net_invested": round(total_invested, 2),
        "total_gain_eur": round(total_gain, 2),
        "total_performance_pct": round(total_perf_pct, 2),
        "items": items
    }


async def compute_allocation_advanced(db: Session) -> dict:
    """Répartition par classe d'actifs, secteur et zone : celle des opérations au prorata de leur montant, sinon celle du compte."""
    accounts = repo.investment_accounts(db)
    values = await account_values(db, accounts)
    groups = AllocationGroups()
    for acc in accounts:
        val_eur = values[acc.id].value_eur
        groups.total += val_eur
        txs = repo.allocated_operations(db, acc.id)
        total_tx_amount = sum(abs(tx.amount) for tx in txs) if txs else 0
        if txs and total_tx_amount > 0:
            for tx in txs:
                groups.add(tx.asset_class, tx.sector, tx.geographic_zone, val_eur * (abs(tx.amount) / total_tx_amount), acc)
        else:
            groups.add(acc.asset_class, acc.sector, acc.geographic_zone, val_eur, acc)
    return groups.result()


async def compute_patrimoine_allocation(db: Session) -> dict:
    """Répartition du patrimoine actif (tous comptes) ; crédits hors camembert : `total_debts_eur`, `net_patrimoine_eur`."""
    accounts = active_accounts(db)
    values = await account_values(db, accounts)
    return patrimoine_items(accounts, values)


def compute_allocation_suggestions(db: Session) -> dict:
    """Valeurs connues (comptes et opérations) et usuelles des classes d'actifs, secteurs et zones (autocomplétion)."""
    def known(account_column, operation_column) -> list[str]:
        rows = repo.distinct_values(db, account_column) + repo.distinct_values(db, operation_column)
        return sorted(list(set([r[0] for r in rows if r[0]])))

    classes = known(Account.asset_class, InvestmentTransaction.asset_class)
    sectors = known(Account.sector, InvestmentTransaction.sector)
    zones = known(Account.geographic_zone, InvestmentTransaction.geographic_zone)
    return {
        "asset_classes": sorted(list(set(classes + DEFAULT_CLASSES))),
        "sectors": sorted(list(set(sectors + DEFAULT_SECTORS))),
        "geographic_zones": sorted(list(set(zones + DEFAULT_ZONES)))
    }
