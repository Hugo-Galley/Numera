"""Calculs purs des métriques (tags, flux d'un compte, kpi-history, calendrier) à partir de lignes déjà chargées."""
from datetime import datetime, timedelta
from typing import Any

POSITIVE_TYPES = ["Entree", "Interets", "Solde Initial", "versement", "dividende"]
NEGATIVE_TYPES = ["Sortie", "retrait"]


def tag_totals(rows: list[Any], rates: dict[str, float]) -> list[dict]:
    """Dépenses par tag converties en EUR, de la plus forte à la plus faible, arrondies à 2 décimales."""
    totals: dict = {}
    for row in rows:
        if row.id not in totals:
            totals[row.id] = {"id": row.id, "name": row.name, "color": row.color, "total_eur": 0.0}
        totals[row.id]["total_eur"] += row.total / rates.get(row.currency, 1.0)
    results = sorted(totals.values(), key=lambda x: x["total_eur"], reverse=True)
    for r in results:
        r["total_eur"] = round(r["total_eur"], 2)
    return results


def net_flow(totals_by_type: dict[str, float]) -> float:
    """Entrées + intérêts − sorties."""
    return totals_by_type.get("Entree", 0.0) + totals_by_type.get("Interets", 0.0) - totals_by_type.get("Sortie", 0.0)


def variation_pct(current: float, previous: float) -> float | None:
    """Variation en % par rapport à la valeur absolue précédente (None si elle est nulle)."""
    if previous == 0:
        return None
    return (current - previous) / abs(previous) * 100


def savings_at(events_by_account: dict[int, list], end: datetime, accounts: dict[int, Any],
               rates: dict[str, float]) -> float:
    """Épargne totale en EUR : dernière valeur connue (relevé ou solde) de chaque compte à `end`."""
    total = 0.0
    for acc_id, items in events_by_account.items():
        matching = [val for date_val, _, val in items if date_val <= end]
        if matching:
            val = matching[-1]
            acc = accounts.get(acc_id)
            total += val / rates.get(acc.currency, 1.0) if acc else val
    return total


def kpi_row(year: int, month: int, rev: float, inte: float, dep: float, inv: float, cat_inv: float,
            epargne: float, account_view: bool) -> dict:
    """Point mensuel du kpi-history (mêmes formules que le budget)."""
    # Comme le budget : seules les sorties catégorisées sont retranchées, jamais les versements
    # (un versement financé par une sortie du mois précédent rendait les dépenses réelles négatives)
    # (vue d'un compte inchangée : les versements y sont les flux du compte, comme dans le budget)
    real_dep = dep - (inv if account_view else cat_inv)
    return {
        "month": month,
        "year": year,
        "label": f"{month}/{year}",
        "base_currency": "EUR",
        "revenus": round(float(rev), 2),
        "interets": round(float(inte), 2),
        "depenses": round(float(dep), 2),
        "depenses_reelles": round(float(real_dep), 2),
        "investissements": round(float(inv), 2),
        "epargne": round(float(epargne), 2),
        "epargne_flow": round(float(rev - real_dep), 2),
        "cash_flow": round(float(rev - dep), 2),
        # Même formule et mêmes bornes que le budget ; None sans revenu (taux sans objet)
        "taux_epargne": round(max(min((rev - real_dep) / rev * 100.0, 100.0), -100.0), 2) if rev >= 1 else None,
    }


def _apply_event(balances: dict[int, float], ev: dict) -> None:
    acc_id = ev.get("account_id")
    if acc_id is None:
        return
    if acc_id not in balances:
        balances[acc_id] = 0.0
    # Une transaction réelle porte son solde courant : on s'y cale exactement
    if not ev.get("is_projected") and ev.get("running_balance") is not None:
        balances[acc_id] = ev["running_balance"]
        return
    amt = ev["amount"]
    if ev["type"] == "Solde Initial":
        balances[acc_id] = amt
    elif ev["type"] in POSITIVE_TYPES:
        balances[acc_id] += amt
    elif ev["type"] in NEGATIVE_TYPES:
        balances[acc_id] -= amt


def daily_balances(events: list[dict], balances: dict[int, float], currencies: dict[int, str],
                   rates: dict[str, float], sim_start: datetime, start_month: datetime, end_month: datetime,
                   account_id: int | None) -> list[dict]:
    """Solde jour par jour (devise du compte, ou EUR en vue globale), du début du mois à sa fin.

    `events` (réels et projetés) sont triés par date ; la simulation part de `sim_start` (au plus tard
    aujourd'hui) avec les soldes d'ouverture `balances`, modifiés en place.
    """
    all_events = sorted(events, key=lambda x: x["date"])
    result = []
    event_idx = 0
    day = sim_start
    while day < end_month:
        while event_idx < len(all_events) and datetime.fromisoformat(all_events[event_idx]["date"]).date() == day.date():
            _apply_event(balances, all_events[event_idx])
            event_idx += 1
        if account_id:
            current = balances.get(account_id, 0.0)
        else:
            current = 0.0
            for a_id, bal in balances.items():
                current += bal / rates.get(currencies.get(a_id, "EUR"), 1.0)
        if day >= start_month:
            result.append({"date": day.date().isoformat(), "balance": round(current, 2)})
        day += timedelta(days=1)
    return result
