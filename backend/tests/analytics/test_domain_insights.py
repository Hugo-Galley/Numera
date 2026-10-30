"""Score de santé financière et anomalies de catégories (calcul pur)."""
from app.domain.insights import category_anomalies, eur, health_score


def test_health_score_full_marks():
    budget = {"taux_epargne": 25.0, "revenus_totaux": 3000.0, "depenses_reelles": 2000.0, "investissements_du_mois": 400.0}
    score = health_score(budget, runway_months=8.0)
    assert score.total_score == 100.0
    assert [m.status for m in score.metrics] == ["good", "good", "good", "good"]


def test_health_score_without_income():
    budget = {"taux_epargne": 0.0, "revenus_totaux": 0.0, "depenses_reelles": 500.0, "investissements_du_mois": 0.0}
    score = health_score(budget, runway_months=1.5)
    assert score.total_score == 7.5
    assert score.metrics[2].status == "critical"


def test_category_anomalies_need_two_months_and_double_average():
    current = {1: 300.0, 2: 50.0, 3: 500.0}
    history = {1: [100.0, 120.0], 2: [10.0, 15.0], 3: [400.0]}
    assert category_anomalies(current, history) == [(1, 300.0, 110.0)]


def test_eur_formats_french_style():
    assert eur(1234.5) == "1 234,50 €"
