"""Détail d'un compte d'investissement (`/investments/{id}`) et historique de performance."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.services.holdings.replay import replay_account
from app.core.portfolio import compute_portfolio, uses_positions
from app.integrations.currency import convert_amount
from app.models.account import Account
from app.repositories.analytics import investments as repo
from app.services.analytics.investments.flows import FEE_KEYWORDS, INTEREST_CATEGORIES, calculate_investment_flows


def _require_investment_account(db: Session, account_id: int) -> Account:
    account = repo.get_account(db, account_id)
    if not account:
        raise NotFoundError("Account not found")
    if account.type not in repo.INVESTMENT_TYPES:
        raise BusinessRuleError("Account must be investissement or assurance_vie")
    return account


async def compute_investment_account(db: Session, account_id: int) -> dict:
    account = _require_investment_account(db, account_id)
    # Flux dans la devise du compte
    flows = await calculate_investment_flows(db, account, datetime.now(), target_currency=account.currency)
    net_invested = flows["net_invested_target"]
    baseline_date = flows["baseline_date"]

    latest = repo.latest_snapshot(db, account_id)
    if latest:
        current_value = float(latest.current_value)
    else:
        # Sans relevé : dernier solde courant, sinon capital net investi
        last_tx = repo.last_transaction(db, account_id)
        current_value = float(last_tx.running_balance) if last_tx else net_invested
    value_source = "snapshot"
    snapshot_value = current_value if latest else None
    if uses_positions(account, await replay_account(db, account.id)):
        p = await compute_portfolio(db, account, history=False)
        current_value, net_invested, value_source = p["value"], p["net_invested"], "positions"
        flows = {**flows, "total_verse_target": net_invested - flows["baseline_val_target"], "total_retire_target": 0.0}

    gain = current_value - net_invested
    performance_pct = (gain / net_invested * 100.0) if net_invested > 0 else 0.0
    return {
        "account_id": account.id,
        "account_name": account.name,
        "currency": account.currency,
        "baseline": {
            "date": baseline_date.isoformat() if baseline_date else None,
            "value": round(flows["baseline_val_target"], 2),
        },
        "totals": {
            "total_verse": round(flows["total_verse_target"], 2),
            "total_retire": round(flows["total_retire_target"], 2),
            "net_invested": round(net_invested, 2),
            "current_value": round(current_value, 2),
            "gain_eur": round(gain, 2),
            "performance_pct": round(performance_pct, 2),
            "value_source": value_source,
            "snapshot_value": round(snapshot_value, 2) if snapshot_value is not None else None,
        },
        "transactions": await _account_movements(db, account, baseline_date),
        "value_series": [
            {
                "id": snap.id,
                "date": snap.date.isoformat(),
                "current_value": round(float(snap.current_value), 2),
                "current_value_raw": round(float(snap.current_value), 2),
                "is_zero_point": bool(snap.is_zero_point),
                "note": snap.note,
            }
            for snap in repo.snapshots(db, account_id)
        ],
    }


async def _account_movements(db: Session, account: Account, baseline_date: datetime | None) -> list[dict]:
    """Opérations et transactions bancaires depuis la base, en devise du compte, par date."""
    movements = []
    for tx in repo.investment_operations(db, account.id, since=baseline_date, ordered=True):
        amount = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
        movements.append({
            "id": tx.id,
            "date": tx.date.isoformat(),
            "type": tx.type,
            "amount": round(amount, 2),
            "original_amount": round(float(tx.original_amount), 2),
            "currency": tx.currency,
            "note": tx.note,
            "asset_class": tx.asset_class,
            "sector": tx.sector,
            "geographic_zone": tx.geographic_zone,
        })
    for tx in repo.account_transactions(db, account.id, since=baseline_date, ordered=True):
        amount = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
        movements.append({
            "id": tx.id,
            "date": tx.date.isoformat(),
            "type": "retrait" if tx.type == "Sortie" else "versement",
            "amount": round(amount, 2),
            "original_amount": round(float(tx.original_amount), 2),
            "currency": tx.currency,
            "note": f"{tx.merchant}{' (' + tx.note + ')' if tx.note else ''}",
            "is_regular": True
        })
    movements.sort(key=lambda x: x["date"])
    return movements


async def compute_performance_history(db: Session, account_id: int) -> dict:
    account = _require_investment_account(db, account_id)
    if uses_positions(account, await replay_account(db, account_id)):
        p = await compute_portfolio(db, account)
        if p["history"]:
            return {
                "items": [
                    {
                        "date": pt["date"],
                        "net_invested": pt["net_invested"],
                        "current_value": pt["value"],
                        "gain_eur": pt["gain"],
                        "performance_pct": pt["performance_pct"] or 0.0,
                        "is_zero_point": pt["date"][:10] == (p["baseline_date"] or "")[:10],
                    }
                    for pt in p["history"]
                ],
                "value_source": "positions",
            }

    zero_point = repo.latest_zero_point(db, account_id)
    baseline_date = zero_point.date if zero_point else None
    baseline_value_raw = float(zero_point.current_value) if zero_point else 0.0
    # Base en devise du compte
    baseline_value = await convert_amount(
        baseline_value_raw, account.currency, account.currency, date=baseline_date.date() if baseline_date else None, db=db
    )
    events = await _flows_by_day(db, account, baseline_date)
    return {"items": _history_series(events, repo.snapshots(db, account_id, since=baseline_date), baseline_value)}


async def _flows_by_day(db: Session, account: Account, baseline_date: datetime | None) -> dict[str, dict[str, float]]:
    """Versements et retraits par jour depuis la base (opérations, puis transactions bancaires)."""
    by_day: dict[str, dict[str, float]] = {}
    txs = repo.investment_operations(db, account.id, since=baseline_date, ordered=True)
    for tx in txs:
        day = by_day.setdefault(tx.date.date().isoformat(), {"versement_target": 0.0, "retrait_target": 0.0})
        if tx.type == "dividende":
            continue
        amount_target = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
        if tx.type == "versement":
            day["versement_target"] += amount_target
        elif tx.type == "retrait":
            day["retrait_target"] += amount_target

    transfer_legs_only = bool(txs) or repo.has_investment_operations(db, account.id)
    for tx in repo.account_transactions(db, account.id, since=baseline_date, transfer_legs_only=transfer_legs_only):
        day = by_day.setdefault(tx.date.date().isoformat(), {"versement_target": 0.0, "retrait_target": 0.0})
        merchant_lower = (tx.merchant or "").lower()
        if tx.type in ["Entree", "Solde Initial"]:
            if tx.type == "Entree":
                if tx.category and tx.category.name in INTEREST_CATEGORIES:
                    continue
                if "vente" in merchant_lower or "dividende" in merchant_lower:
                    continue
            day["versement_target"] += await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
        elif tx.type == "Sortie":
            if any(k in merchant_lower for k in FEE_KEYWORDS):
                continue
            day["retrait_target"] += await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
    return by_day


def _history_series(events: dict[str, dict[str, float]], snaps: list, baseline_value: float) -> list[dict]:
    """Capital net investi cumulé et valeur à chaque relevé."""
    snaps_by_day = {s.date.date().isoformat(): s for s in snaps}
    running_verse = running_retire = 0.0
    series = []
    for day_str in sorted(set(events.keys()) | {s.date.date().isoformat() for s in snaps}):
        event = events.get(day_str, {"versement_target": 0.0, "retrait_target": 0.0})
        running_verse += event["versement_target"]
        running_retire += event["retrait_target"]
        snap = snaps_by_day.get(day_str)
        if snap:
            net_invested = baseline_value + running_verse - running_retire
            current_value = float(snap.current_value)
            gain = current_value - net_invested
            performance_pct = (gain / net_invested * 100.0) if net_invested > 0 else 0.0
            series.append({
                "date": snap.date.isoformat(),
                "net_invested": round(net_invested, 2),
                "current_value": round(current_value, 2),
                "gain_eur": round(gain, 2),  # en devise du compte malgré le nom
                "performance_pct": round(performance_pct, 2),
                "is_zero_point": bool(snap.is_zero_point),
            })
    return series
