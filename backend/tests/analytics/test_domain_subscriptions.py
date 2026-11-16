"""Coût mensuel et annuel d'une récurrence en EUR."""
import pytest

from app.domain.subscriptions import recurring_costs


def test_recurring_costs_by_frequency_in_eur():
    assert recurring_costs(10.0, "monthly", 1.0) == (10.0, 120.0)
    assert recurring_costs(120.0, "yearly", 1.0) == pytest.approx((10.0, 120.0))
    assert recurring_costs(21.6, "monthly", 1.08) == pytest.approx((20.0, 240.0))


def test_unknown_frequency_costs_nothing():
    assert recurring_costs(10.0, "fortnightly", 1.0) == (0.0, 0.0)


@pytest.mark.parametrize("category", [
    "Assurances", "assurance auto", "Mutuelle", "Santé", "SANTE", "Logement", "Loyer", "Charges copro",
    "Énergie", "Electricité", "Gaz", "Eau", "Téléphonie", "Mobile", "Internet", "Box internet",
    "Crédit immobilier", "Prêt auto", "Emprunt",
])
def test_essential_categories_by_default(category):
    from app.domain.subscriptions import default_is_essential

    assert default_is_essential(category) is True


@pytest.mark.parametrize("category", [None, "", "Abonnement", "Sortie", "Sport", "Shopping", "Nourriture", "Voyages",
                                      "Interprète", "Chargeur"])
def test_other_categories_are_not_essential_by_default(category):
    from app.domain.subscriptions import default_is_essential

    assert default_is_essential(category) is False


def test_manual_choice_wins_over_category():
    from app.domain.subscriptions import effective_essential

    assert effective_essential(None, "Assurances") == (True, "auto")
    assert effective_essential(None, "Abonnement") == (False, "auto")
    assert effective_essential(False, "Assurances") == (False, "manual")
    assert effective_essential(True, "Abonnement") == (True, "manual")


def test_reste_a_vivre_deducts_essential_or_all_charges():
    from app.domain.subscriptions import RecurringLine, reste_a_vivre

    lines = [
        RecurringLine(flow_type="Entree", kind="other", in_kind_total=True, is_essential=False, monthly_cost=2000.0),
        RecurringLine(flow_type="Interets", kind="other", in_kind_total=True, is_essential=False, monthly_cost=10.0),
        RecurringLine(flow_type="Sortie", kind="subscriptions", in_kind_total=True, is_essential=True, monthly_cost=800.0),
        RecurringLine(flow_type="Sortie", kind="subscriptions", in_kind_total=True, is_essential=False, monthly_cost=50.0),
        # hors calcul : en pause / non prélevée, épargne, investissement, flux titres
        RecurringLine(flow_type="Sortie", kind="subscriptions", in_kind_total=False, is_essential=True, monthly_cost=99.0),
        RecurringLine(flow_type="Entree", kind="other", in_kind_total=False, is_essential=False, monthly_cost=500.0),
        RecurringLine(flow_type="Sortie", kind="investments", in_kind_total=True, is_essential=False, monthly_cost=300.0),
        RecurringLine(flow_type="achat", kind="other", in_kind_total=True, is_essential=False, monthly_cost=100.0),
    ]
    result = reste_a_vivre(lines)
    assert result.revenus_recurrents == 2010.0
    assert result.charges_essentielles == 800.0
    assert result.charges_non_essentielles == 50.0
    assert result.reste_a_vivre_essentiel == 1210.0
    assert result.reste_a_vivre_total == 1160.0
