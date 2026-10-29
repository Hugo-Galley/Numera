"""Calculs purs des rapports : écarts d'un mois à l'autre, blocs money-flow, graphe Sankey, projection de trésorerie."""
from datetime import datetime, timedelta
from typing import Any

from app.schemas.insight import MoneyFlowBlock, ProjectionPoint


def calc_diff(curr: float, prev: float) -> tuple[float, float]:
    """Écart et variation en % par rapport à la valeur absolue précédente (0 si elle est nulle)."""
    diff = curr - prev
    pct = (diff / abs(prev) * 100.0) if prev != 0 else 0.0
    return round(diff, 2), round(pct, 2)


def money_flow_block(val_curr: float, val_prev: float, income: float) -> MoneyFlowBlock:
    """Montant du mois, part des revenus et écart avec le mois précédent."""
    diff = val_curr - val_prev
    diff_pct = (diff / abs(val_prev) * 100) if val_prev != 0 else 0
    pct_inc = (val_curr / income * 100) if income != 0 else 0
    return MoneyFlowBlock(
        amount=round(val_curr, 2),
        percentage=round(pct_inc, 1),
        diff_prev_month=round(diff, 2),
        diff_prev_month_pct=round(diff_pct, 1)
    )


def top_items(totals: dict[str, float], limit: int = 5) -> list[dict]:
    return sorted([{"name": k, "amount": v} for k, v in totals.items()], key=lambda x: x["amount"], reverse=True)[:limit]


class _Graph:
    def __init__(self) -> None:
        self.nodes: list[dict] = []
        self.links: list[dict] = []

    def node(self, name: str, color: str | None = None, category_id: int | None = None) -> int:
        node = {"name": name, "color": color}
        if category_id is not None:
            node["category_id"] = category_id  # nœud de catégorie de dépense : cliquable (drill-down)
        self.nodes.append(node)
        return len(self.nodes) - 1

    def link(self, source: int, target: int, value: float, color: str | None) -> None:
        self.links.append({"source": source, "target": target, "value": round(value, 2), "color": color})


def _group_expenses(cat_expenses: dict[Any, dict]) -> tuple[list[str], dict, dict, list]:
    """Catégories regroupées par groupe parent (évite les croisements), groupes et catégories triés par total."""
    grouped: dict[str, list[dict]] = {}
    ungrouped: list[dict] = []
    for data in cat_expenses.values():
        cat, total = data["obj"], data["total"]
        if total <= 0:
            continue
        item = {"name": cat.name, "color": cat.color, "total": total, "id": cat.id}
        if cat.group:
            grouped.setdefault(cat.group, []).append(item)
        else:
            ungrouped.append(item)
    group_totals = {g_name: sum(item["total"] for item in items) for g_name, items in grouped.items()}
    sorted_groups = sorted(grouped.keys(), key=lambda g: group_totals[g], reverse=True)
    for g_name in grouped:
        grouped[g_name] = sorted(grouped[g_name], key=lambda x: x["total"], reverse=True)
    return sorted_groups, grouped, group_totals, sorted(ungrouped, key=lambda x: x["total"], reverse=True)


def sankey_graph(income_sources: list[dict], total_income: float, invest_total: float,
                 cat_expenses: dict[Any, dict]) -> dict:
    """Revenus → Budget → (investissements, épargne, groupes → catégories) ; le nœud Budget est équilibré."""
    g = _Graph()
    budget = g.node("Budget", "#94a3b8")
    for src in income_sources:
        g.link(g.node(src["name"], src["color"]), budget, src["total"], src["color"])
    if invest_total > 0:
        g.link(budget, g.node("Investissements", "#6366f1"), invest_total, "#6366f1")

    # Épargne : ce qui reste une fois dépenses et investissements sortis, sur les mêmes flux que le diagramme
    spent_total = sum(data["total"] for data in cat_expenses.values() if data["total"] > 0)
    savings_total = total_income - spent_total - max(invest_total, 0.0)
    if savings_total > 0:
        g.link(budget, g.node("Épargne", "#10b981"), savings_total, "#10b981")
    elif savings_total < 0:
        # Dépenses supérieures aux revenus : un flux « Déficit » entre dans le Budget
        g.link(g.node("Déficit / Trésorerie", "#f43f5e"), budget, abs(savings_total), "#fecdd3")
        total_income += abs(savings_total)

    sorted_groups, grouped, group_totals, ungrouped = _group_expenses(cat_expenses)
    group_nodes = {}
    for g_name in sorted_groups:
        group_nodes[g_name] = g.node(g_name, "#64748b")
        g.link(budget, group_nodes[g_name], group_totals[g_name], "#cbd5e1")
    for g_name in sorted_groups:
        for item in grouped[g_name]:
            g.link(group_nodes[g_name], g.node(item["name"], item["color"], item["id"]), item["total"], item["color"])
    for item in ungrouped:
        g.link(budget, g.node(item["name"], item["color"], item["id"]), item["total"], item["color"])

    # Reliquat (arrondis, flux non suivis) au-delà d'un euro : nœud d'ajustement
    total_out = sum(link["value"] for link in g.links if link["source"] == budget)
    diff = total_income - total_out
    if diff > 1.0:
        g.link(budget, g.node("Reliquat / Ajustement", "#94a3b8"), diff, "#cbd5e1")
    return {"nodes": g.nodes, "links": g.links}


def simulate_cashflow(events: list[Any], current_bal: float, now: datetime,
                      end_date: datetime) -> tuple[list[ProjectionPoint], float, float, str]:
    """Solde projeté jour par jour : points, solde final, point bas et sa date. `events` triés par date."""
    points: list[ProjectionPoint] = []
    simulated_bal = current_bal
    low_point = current_bal
    low_point_date = now.date().isoformat()
    event_idx = 0
    day = now
    while day <= end_date:
        daily_change = 0.0
        while event_idx < len(events) and datetime.fromisoformat(events[event_idx].date).date() == day.date():
            ev = events[event_idx]
            if ev.is_income:
                simulated_bal += ev.amount
                daily_change += ev.amount
            else:
                simulated_bal -= ev.amount
                daily_change -= ev.amount
            event_idx += 1
        if simulated_bal < low_point:
            low_point = simulated_bal
            low_point_date = day.date().isoformat()
        points.append(ProjectionPoint(date=day.date().isoformat(), balance=round(simulated_bal, 2), change=round(daily_change, 2)))
        day += timedelta(days=1)
    return points, simulated_bal, low_point, low_point_date
