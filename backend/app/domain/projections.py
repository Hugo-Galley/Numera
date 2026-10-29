"""Projections pures : prévision de patrimoine, indépendance financière (FIRE), simulation (Monte-Carlo)."""
import json
import math
import random

from app.schemas.insight import FirePoint, FireScenario, WealthForecastReturnItem, WealthSimulationPoint

FIRE_MAX_YEARS = 80


# --- Prévision de patrimoine ---

def return_breakdown(measured: float, unmeasured: float, other: float, observed_pct: float | None,
                     investment_return_pct: float | None, savings_return_pct: float | None) -> list[WealthForecastReturnItem]:
    """Rendement par type de solde : le XIRR constaté ne s'applique qu'aux comptes valorisés par positions."""
    invest_balance = measured + unmeasured
    other_rate = savings_return_pct if savings_return_pct is not None else 0.0
    other_item = WealthForecastReturnItem(
        type="autres", balance=round(other, 2), rate_pct=round(other_rate, 2),
        source="manual" if savings_return_pct is not None else "none",
    )
    if investment_return_pct is not None:
        invest_items = [WealthForecastReturnItem(
            type="investissement", balance=round(invest_balance, 2), rate_pct=round(investment_return_pct, 2), source="manual",
        )]
    elif observed_pct is None:
        invest_items = [WealthForecastReturnItem(
            type="investissement", balance=round(invest_balance, 2), rate_pct=0.0, source="none",
        )]
    else:
        invest_items = [WealthForecastReturnItem(
            type="investissement", balance=round(measured, 2), rate_pct=round(observed_pct, 2), source="observed",
        )]
        if unmeasured > 0:
            invest_items.append(WealthForecastReturnItem(
                type="investissement_non_mesure", balance=round(unmeasured, 2), rate_pct=0.0, source="none",
            ))
    return invest_items + [other_item]


def weighted_return(breakdown: list[WealthForecastReturnItem], positive_total: float) -> float:
    """Rendement annuel moyen pondéré par les soldes (%)."""
    weighted = sum(i.balance * i.rate_pct for i in breakdown)
    return weighted / positive_total if positive_total > 0 else 0.0


def savings_window(history: list[dict], year: int, month: int) -> list[dict]:
    """Douze derniers mois complets du kpi-history, sans les mois de tête sans dépense (avant le début du suivi)."""
    completed = [r for r in history if not (r["year"] == year and r["month"] == month)]
    rows = completed[-12:] if completed else history
    # Seuls des intérêts d'épargne avant le suivi : ces mois tireraient la moyenne vers zéro
    first_active = next(
        (i for i, r in enumerate(rows) if float(r["revenus"]) - float(r["epargne_flow"]) > 0.005), None
    )
    return rows[first_active:] if first_active else rows


def monthly_rate(annual_pct: float) -> float:
    return (1 + annual_pct / 100.0) ** (1 / 12) - 1


def project_wealth(start: float, monthly: float, rate: float, years: int) -> list[float]:
    """Valeur en fin de chaque année (année 0 comprise), versement mensuel et capitalisation mensuelle."""
    value = start
    values = [value]
    for _ in range(years):
        for _ in range(12):
            value = value * (1 + rate) + monthly
        values.append(value)
    return values


# --- FIRE ---

def months_to_target(wealth: float, monthly: float, monthly_rate: float, target: float) -> int | None:
    """Mois avant que le patrimoine (euros constants) atteigne la cible, None au-delà de FIRE_MAX_YEARS."""
    if wealth >= target:
        return 0
    for month in range(1, FIRE_MAX_YEARS * 12 + 1):
        wealth = wealth * (1 + monthly_rate) + monthly
        if wealth >= target:
            return month
    return None


def fire_target(annual_expenses: float, withdrawal_rate_pct: float) -> float:
    return annual_expenses / (withdrawal_rate_pct / 100.0)


def real_return(nominal_pct: float, inflation_pct: float) -> float:
    """Rendement réel en % : (1 + nominal) / (1 + inflation) − 1."""
    return ((1 + nominal_pct / 100.0) / (1 + inflation_pct / 100.0) - 1) * 100.0


def years_to_fi(wealth: float, monthly: float, annual: float, rate: float, withdrawal_rate_pct: float) -> float | None:
    if annual <= 0:
        return 0.0
    months_needed = months_to_target(wealth, monthly, rate, fire_target(annual, withdrawal_rate_pct))
    return None if months_needed is None else round(months_needed / 12.0, 1)


def fire_points(wealth: float, savings: float, rate: float, target: float, years_needed: float | None,
                this_year: int) -> list[FirePoint]:
    """Courbe jusqu'à deux ans après l'indépendance (40 ans si hors d'atteinte, 80 au plus)."""
    horizon = min(int(math.ceil(years_needed)) + 2 if years_needed is not None else 40, FIRE_MAX_YEARS)
    points = []
    value = wealth
    for year in range(horizon + 1):
        points.append(FirePoint(year=this_year + year, wealth=round(value, 2), target=round(target, 2)))
        for _ in range(12):
            value = value * (1 + rate) + savings
    return points


def fire_scenarios(wealth: float, savings: float, expenses: float, rate: float,
                   withdrawal_rate_pct: float) -> list[FireScenario]:
    """Effet d'un effort d'épargne supplémentaire ou de dépenses réduites."""
    return [
        FireScenario(label=label, monthly_savings=round(m, 2), annual_expenses=round(a, 2),
                     years_to_fi=years_to_fi(wealth, m, a, rate, withdrawal_rate_pct))
        for label, m, a in (
            ("Actuel", savings, expenses),
            ("+100 €/mois", savings + 100, expenses),
            ("+250 €/mois", savings + 250, expenses),
            ("+500 €/mois", savings + 500, expenses),
            ("Dépenses −10 %", savings + expenses * 0.10 / 12, expenses * 0.90),
        )
    ]


# --- Simulation ---

def parse_events(events: str | None) -> dict[int, list[dict]]:
    """Événements ponctuels (JSON `[{year, amount, label}]`) groupés par année ; entrées invalides ignorées."""
    parsed = []
    if events:
        try:
            parsed = json.loads(events)
            if not isinstance(parsed, list):
                parsed = []
        except Exception:
            parsed = []
    by_year: dict[int, list[dict]] = {}
    for ev in parsed:
        try:
            y = int(ev.get("year", 0))
            amt = float(ev.get("amount", 0.0))
            lbl = str(ev.get("label", "Événement"))
            by_year.setdefault(y, []).append({"amount": amt, "label": lbl})
        except (ValueError, TypeError):
            continue
    return by_year


def _run_trial(initial_capital: float, monthly_contribution: float, years: int, monthly_rate_det: float,
               monthly_mean: float, monthly_std: float, volatile: bool, inflation_rate_pct: float,
               contribution_indexation_pct: float, tax_rate_pct: float, tax_deferred: bool,
               events: dict[int, list[dict]]) -> list[tuple[float, float, float, float, float]]:
    """Une trajectoire : par année (valeur nette, valeur réelle, intérêts nets, impôt, versements cumulés)."""
    current_total = initial_capital
    cumulative_contributions = cumulative_interest = cumulative_tax_paid = cumulative_events = 0.0
    rows = []
    for y in range(1, years + 1):
        monthly_contrib = monthly_contribution * (1 + contribution_indexation_pct / 100.0) ** (y - 1)
        interest_this_year = contributions_this_year = 0.0
        for _ in range(12):
            r_m = random.normalvariate(monthly_mean, monthly_std) if volatile else monthly_rate_det
            interest_m = current_total * r_m
            interest_this_year += interest_m
            current_total += interest_m + monthly_contrib
            contributions_this_year += monthly_contrib
        cumulative_interest += interest_this_year
        cumulative_contributions += contributions_this_year
        # Impôt annuel si non différé
        if not tax_deferred and tax_rate_pct > 0 and interest_this_year > 0:
            tax_y = interest_this_year * (tax_rate_pct / 100.0)
            current_total -= tax_y
            cumulative_tax_paid += tax_y
            cumulative_interest -= tax_y
        if y in events:
            for ev in events[y]:
                current_total += ev["amount"]
                cumulative_events += ev["amount"]
            if current_total < 0:
                current_total = 0.0
        inflation_factor = (1 + inflation_rate_pct / 100.0) ** y
        if tax_deferred and tax_rate_pct > 0:
            gain_y = current_total - initial_capital - cumulative_contributions - cumulative_events
            tax_due_y = max(0.0, gain_y * (tax_rate_pct / 100.0))
            net_nominal = current_total - tax_due_y
            rows.append((net_nominal, net_nominal / inflation_factor, cumulative_interest - tax_due_y, tax_due_y,
                         cumulative_contributions))
        else:
            rows.append((current_total, current_total / inflation_factor, cumulative_interest, cumulative_tax_paid,
                         cumulative_contributions))
    return rows


def _event_label(events: dict[int, list[dict]], y: int) -> str | None:
    if y not in events:
        return None
    return ", ".join(f"{ev['label']} ({'+' if ev['amount'] >= 0 else ''}{int(ev['amount'])}€)" for ev in events[y])


def simulate_wealth(initial_capital: float, monthly_contribution: float, annual_return_pct: float, years: int,
                    volatility_pct: float, inflation_rate_pct: float, contribution_indexation_pct: float,
                    tax_rate_pct: float, tax_deferred: bool, events: dict[int, list[dict]]) -> list[WealthSimulationPoint]:
    """Simulation année par année ; avec volatilité, 1 000 tirages et percentiles 10/50/90."""
    num_trials = 1000 if volatility_pct > 0 else 1
    annual_rate_decimal = annual_return_pct / 100.0
    monthly_rate_det = (1 + annual_rate_decimal) ** (1/12) - 1 if annual_rate_decimal > -1 else -1.0
    trial_args = (initial_capital, monthly_contribution, years, monthly_rate_det, annual_rate_decimal / 12.0,
                  volatility_pct / 100.0 / (12.0 ** 0.5), volatility_pct > 0, inflation_rate_pct,
                  contribution_indexation_pct, tax_rate_pct, tax_deferred, events)
    # by_year[y][k] : liste des tirages de la grandeur k (valeur, réelle, intérêts, impôt, versements)
    by_year = [[[initial_capital] * num_trials, [initial_capital] * num_trials, [0.0] * num_trials,
                [0.0] * num_trials, [0.0] * num_trials]]
    by_year += [[[], [], [], [], []] for _ in range(years)]
    for _ in range(num_trials):
        for y, row in enumerate(_run_trial(*trial_args), start=1):
            for k, value in enumerate(row):
                by_year[y][k].append(value)
    if volatility_pct > 0:
        for y in range(years + 1):
            for k in range(4):  # les versements ne sont pas triés (identiques d'un tirage à l'autre)
                by_year[y][k].sort()
        idx = (int(0.10 * num_trials), int(0.50 * num_trials), int(0.90 * num_trials))
    else:
        idx = (0, 0, 0)
    return [_point(initial_capital, y, by_year[y], idx, _event_label(events, y)) for y in range(years + 1)]


def _point(initial_capital: float, y: int, values: list[list[float]], idx: tuple[int, int, int],
           event_applied: str | None) -> WealthSimulationPoint:
    value, real, interest, tax, contributions = values
    p10, p50, p90 = idx
    return WealthSimulationPoint(
        year=y,
        initial_capital=round(initial_capital, 2),
        total_contributions=round(contributions[p50], 2),
        total_interest=round(interest[p50], 2),
        total_value=round(value[p50], 2),
        total_value_real=round(real[p50], 2),
        total_value_p10=round(value[p10], 2),
        total_value_p50=round(value[p50], 2),
        total_value_p90=round(value[p90], 2),
        total_value_p10_real=round(real[p10], 2),
        total_value_p50_real=round(real[p50], 2),
        total_value_p90_real=round(real[p90], 2),
        total_tax_paid=round(tax[p50], 2),
        event_applied=event_applied,
    )
