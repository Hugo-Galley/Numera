"""Coût des récurrences (calcul pur)."""

# Multiplicateurs (coût mensuel, coût annuel) par fréquence de récurrence
MONTHS_PER_PERIOD_FACTOR = {
    "daily": {"monthly": 30.0, "annual": 365.0},
    "weekly": {"monthly": 4.33, "annual": 52.0},
    "monthly": {"monthly": 1.0, "annual": 12.0},
    "quarterly": {"monthly": 1 / 3, "annual": 4.0},
    "yearly": {"monthly": 1 / 12, "annual": 1.0},
    "annual": {"monthly": 1 / 12, "annual": 1.0},  # ancien libellé
}


def recurring_costs(amount: float, frequency: str, rate: float) -> tuple[float, float]:
    """Coût mensuel et annuel en EUR d'une récurrence (montant dans sa devise, `rate` = taux EUR→devise)."""
    factor = MONTHS_PER_PERIOD_FACTOR.get(frequency)
    monthly_cost = float(amount) * factor["monthly"] / rate if factor else 0.0
    annual_cost = float(amount) * factor["annual"] / rate if factor else 0.0
    return monthly_cost, annual_cost
