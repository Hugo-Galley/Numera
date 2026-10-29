"""Score de santé financière et détection d'anomalies (calcul pur)."""
from app.schemas.insight import HealthScore, MetricDetail


def eur(value: float) -> str:
    """Montant à la française pour les textes : « 1 234,56 € »."""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " €"


def health_score(budget_data: dict, runway_months: float) -> HealthScore:
    """Score sur 100 : taux d'épargne (30), fonds de sécurité (30), trésorerie positive (20), investissement (20)."""
    revenus = budget_data["revenus_totaux"]
    savings_rate = budget_data["taux_epargne"]
    investissements = budget_data["investissements_du_mois"]

    # Taux d'épargne : objectif 20 %
    sr_score = min(max(savings_rate / 20.0 * 30.0, 0.0), 30.0)
    # Fonds de sécurité : objectif 6 mois
    runway_score = min(runway_months / 6.0 * 30.0, 30.0)
    # Trésorerie : revenus > dépenses réelles
    cashflow = revenus - budget_data["depenses_reelles"]
    cf_score = 20.0 if cashflow > 0 else 0.0
    # Investissement : objectif 10 % des revenus
    inv_ratio = min(investissements / revenus * 100.0, 100.0) if revenus > 0 else 0.0
    inv_score = min(inv_ratio / 10.0 * 20.0, 20.0)

    metrics = [
        MetricDetail(
            name="Taux d'Épargne", score=round(sr_score, 1), max_score=30.0, value=round(savings_rate, 1), unit="%",
            status="good" if savings_rate >= 20 else "warning" if savings_rate >= 10 else "critical"
        ),
        MetricDetail(
            name="Fonds de Sécurité", score=round(runway_score, 1), max_score=30.0, value=round(runway_months, 1),
            unit="mois", status="good" if runway_months >= 6 else "warning" if runway_months >= 3 else "critical"
        ),
        MetricDetail(
            name="Flux de Trésorerie", score=cf_score, max_score=20.0, value=round(cashflow, 2), unit="€",
            status="good" if cashflow > 0 else "critical"
        ),
        MetricDetail(
            name="Ratio d'Investissement", score=round(inv_score, 1), max_score=20.0, value=round(inv_ratio, 1),
            unit="%", status="good" if inv_ratio >= 10 else "warning" if inv_ratio >= 5 else "critical"
        ),
    ]
    return HealthScore(total_score=round(sum(m.score for m in metrics), 1), metrics=metrics)


def category_anomalies(current_totals: dict, histories: dict) -> list[tuple]:
    """(catégorie, total du mois, moyenne) des catégories à plus de 2× leur moyenne (moyenne > 20 €, 2 mois au moins)."""
    anomalies = []
    for cat_id, current_total in current_totals.items():
        history = histories.get(cat_id, [])
        if len(history) >= 2:  # au moins deux mois pour une moyenne parlante
            avg = sum(history) / len(history)
            if avg > 20 and current_total > (avg * 2.0):
                anomalies.append((cat_id, current_total, avg))
    return anomalies
