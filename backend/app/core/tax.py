"""Calculs fiscaux par enveloppe. Fonctions pures : aucune base de données, aucun appel réseau."""
from datetime import date

from app.core.tax_rules import TaxRules

PEA_MILESTONE_YEARS = 5
AV_MILESTONE_YEARS = 8


def years_between(start: date, end: date) -> float:
    """Années écoulées entre deux dates (calendaires, fractionnaires)."""
    whole = end.year - start.year - ((end.month, end.day) < (start.month, start.day))
    day = 28 if (start.month == 2 and start.day == 29) else start.day
    anniversary = date(start.year + whole, start.month, day)
    next_anniversary = date(anniversary.year + 1, anniversary.month, day)
    return whole + (end - anniversary).days / max((next_anniversary - anniversary).days, 1)


def _blank(**overrides) -> dict:
    status = {
        "current": None, "ceiling": None, "remaining": None, "used_pct": None,
        "age_years": None, "milestone_years": None, "milestone_reached": None,
        "estimated_tax_saving": None, "allowance": None, "alerts": [],
    }
    status.update(overrides)
    return status


def _room(current: float, ceiling: float) -> tuple[float, float]:
    return max(ceiling - current, 0.0), (current / ceiling * 100.0 if ceiling > 0 else 0.0)


def pea_status(contributions: float, opened_at: date | None, withdrawals: list[date], today: date, rules: TaxRules) -> dict:
    """Versements cumulés (un retrait ne restitue pas de place) et ancienneté du plan."""
    remaining, used_pct = _room(contributions, rules.pea_ceiling)
    alerts: list[str] = []
    age = reached = None
    if opened_at is None:
        alerts.append("Date d'ouverture manquante : renseigne-la dans les paramètres du compte.")
    else:
        age = years_between(opened_at, today)
        reached = age >= PEA_MILESTONE_YEARS
        if any(years_between(opened_at, w) < PEA_MILESTONE_YEARS for w in withdrawals):
            alerts.append("Retrait avant 5 ans : la fiscalité avantageuse du PEA est perdue.")
    if contributions > rules.pea_ceiling:
        alerts.append("Plafond de versements du PEA dépassé.")
    return _blank(
        current=contributions, ceiling=rules.pea_ceiling, remaining=remaining, used_pct=used_pct,
        age_years=age, milestone_years=PEA_MILESTONE_YEARS, milestone_reached=reached, alerts=alerts,
    )


def per_deduction_ceiling(prior_year_income: float, rules: TaxRules) -> float:
    """10 % des revenus pro de N-1, borné entre le plancher et le plafond de l'année."""
    return min(max(prior_year_income * rules.per_rate, rules.per_floor), rules.per_ceiling)


def per_status(contributed_this_year: float, prior_year_income: float, tmi_pct: float, rules: TaxRules) -> dict:
    """Versements de l'année civile face au plafond de déduction, économie d'impôt = déductible × TMI."""
    ceiling = per_deduction_ceiling(prior_year_income, rules)
    remaining, used_pct = _room(contributed_this_year, ceiling)
    alerts = []
    if contributed_this_year > ceiling:
        alerts.append("Versements supérieurs au plafond de déduction : l'excédent n'est pas déductible.")
    return _blank(
        current=contributed_this_year, ceiling=ceiling, remaining=remaining, used_pct=used_pct,
        estimated_tax_saving=min(contributed_this_year, ceiling) * tmi_pct / 100.0, alerts=alerts,
    )


def livret_a_status(balance: float, rules: TaxRules) -> dict:
    remaining, used_pct = _room(balance, rules.livret_a_ceiling)
    alerts = ["Solde supérieur au plafond du Livret A."] if balance > rules.livret_a_ceiling else []
    return _blank(current=balance, ceiling=rules.livret_a_ceiling, remaining=remaining, used_pct=used_pct, alerts=alerts)


def av_status(opened_at: date | None, household: str, today: date, rules: TaxRules) -> dict:
    """Ancienneté face aux 8 ans et abattement annuel applicable aux gains de rachat."""
    allowance = rules.av_allowance_couple if household == "couple" else rules.av_allowance_single
    if opened_at is None:
        return _blank(
            milestone_years=AV_MILESTONE_YEARS, allowance=allowance,
            alerts=["Date d'ouverture manquante : renseigne-la dans les paramètres du compte."],
        )
    age = years_between(opened_at, today)
    return _blank(age_years=age, milestone_years=AV_MILESTONE_YEARS, milestone_reached=age >= AV_MILESTONE_YEARS, allowance=allowance)
